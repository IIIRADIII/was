"""Скрипт управляет объектами WAS.

Скрипт выполняет операции над указанными объектами
Скрипт принимает от трех аргументов, первый - тип объекта(application/cluster), второй - имя объекта, третий - операция
Например:
was.py application UfoServices restart


"""

import sys
import time
import os
import java.lang.System as jsys


'''
Script classes
Logger - using for better log capabilities
'''


class Logger:
    class __Logger:
        def __init__(self):
            pass

    def logstartinfo(self, string):
        print ""
        print "===================================================================================================="
        print string

    def logseparator(self):
        print "----------------------------------------------------------------------------------------------------"
        print "----------------------------------------------------------------------------------------------------"
        print "----------------------------------------------------------------------------------------------------"
        print "----------------------------------------------------------------------------------------------------"

    def logendinfo(self):
        print "WORK DONE"
        print "===================================================================================================="

    def logerror(self, string):
        print ""
        print "===================================================================================================="
        print string
        print "===================================================================================================="
        print ""

    def loginfo(self, string):
        print(string)


'''
WebSphere manage classes
Application - using for managing application.
'''

class Cluster:
    def __init__(self, name):
        self.name = name
        self.object = AdminControl.completeObjectName('type=Cluster,name=' + self.name + ',*')
        self.id = AdminConfig.getid('/ServerCluster:' + self.name)
        self.members = AdminConfig.list('ClusterMember', self.id).split(lineSeparator)

    def status(self):
        state = AdminControl.getAttribute(self.object,"state")
        if state == "websphere.cluster.running":
            return "started"
        elif state == "websphere.cluster.stopped":
            return "stopped"

    def stop(self):
        if self.status() == "stopped":
            print "Cluster " + self.name + " already stopped"
        else:
            AdminControl.invoke(self.object, 'stop')
            while self.status() != "stopped":
                print "Waiting till cluster stops. Sleep for 5 seconds"
                time.sleep(5)
            print "Cluster " + self.name + " successfully stopped"

    def start(self):
        if self.status() == "started":
            print "Cluster " + self.name + " already started"
        else:
            AdminControl.invoke(self.object, 'start')
            while self.status() != "started":
                print "Waiting till cluster starts. Sleep for 5 seconds"
                time.sleep(5)
            print "Cluster " + self.name + " successfully started"

    def restart(self):
        print "Trying to restart cluster"
        self.stop()
        self.start()
        print "Cluster successfully restarted"

class Application:
    def __init__(self, name):
        self.name = name
        self.cell = AdminConfig.list('Cell').split('(')[0]
        self.cluster = {}
        self.servers = []
        self._getmodules(name)
        self._getcontextroot(name)

    def _getmodules(self, name):
        modsline = AdminApp.listModules(name, '-server')
        modswithoutname = modsline[modsline.find(':') + 1:]
        mods = modswithoutname.split(':')
        for mod in mods:
            modparams = {}
            curmod = mod.split(',')
            for cur in curmod:
                par, value = cur.split('=')
                modparams[par] = value
            if modparams.has_key('cluster'):
                cluster = Cluster(modparams['cluster'])
                self.cluster['name'] = cluster.name
                self.cluster['object'] = cluster.object
                clusterMembers = cluster.members
                for cm in clusterMembers:
                    serverparams = {}
                    servername = cm[:cm.find('(cell')]
                    serverappmanager = AdminControl.completeObjectName(
                        'type=ApplicationManager,process=' + servername + ',*')
                    serverobject = AdminControl.completeObjectName('WebSphere:type=Server,name=' + servername + ',*')
                    servernodename = AdminControl.getAttribute(serverobject, 'nodeName')
                    servernodeobject = AdminControl.completeObjectName(
                        'WebSphere:type=NodeAgent,name=' + servernodename)
                    serverparams['name'] = servername
                    serverparams['object'] = serverobject
                    serverparams['applicationManager'] = serverappmanager
                    serverparams['nodeName'] = servernodename
                    serverparams['nodeObject'] = servernodeobject
                    self.servers.append(serverparams)
            else:
                self.cluster['name'] = "None"
                serverparams = {}
                servername = modparams['server']
                serverappmanager = AdminControl.completeObjectName(
                    'type=ApplicationManager,process=' + servername + ',*')
                serverobject = AdminControl.completeObjectName('WebSphere:type=Server,name=' + servername + ',*')
                servernodename = modparams['node']
                servernodeobject = AdminControl.completeObjectName(
                    'WebSphere:type=NodeAgent,name=' + servernodename)
                serverparams['name'] = servername
                serverparams['object'] = serverobject
                serverparams['applicationManager'] = serverappmanager
                serverparams['nodeName'] = servernodename
                serverparams['nodeObject'] = servernodeobject
                self.servers.append(serverparams)

    def _getcontextroot(self, name):
        elems = wsadmin_to_list(AdminApp.view(name, '-CtxRootForWebMod'))
        i = 1
        self.contextroot = elems[len(elems) - i].split("  ")[1]

    def __str__(self):
        if app.cluster['name'] != 'None':
            return "App " + self.name + " with context root " + self.contextroot + \
                   " installed on " + self.cluster['name']
        else:
            return "App " + self.name + " with context root " + self.contextroot + \
                   " installed on: " + self.servers[0]['name']

    def status(self):
        appmbean = AdminControl.queryNames('type=Application,name=' + self.name + ',*')
        if len(appmbean) != 0:
            return "started"
        return "stopped"

    def isready(self):
        return AdminApp.isAppReady(self.name)

    def stop(self):
        if self.status() != "started":
            print "App " + self.name + "already stopped"
        else:
            AdminControl.invoke(self.servers[0]['applicationManager'], 'stopApplication', self.name)
            while self.status() != "stopped":
                time.sleep(5)
                logger.loginfo("Waiting till " + self.name + " application stops")
            logger.loginfo("Application successfully stopped")

    def start(self):
        if self.status() != "stopped":
            print "App " + self.name + "already started"
        else:
            AdminControl.invoke(self.servers[0]['applicationManager'], 'startApplication', self.name)
            while AdminApp.isAppReady(app.name) != "true" and self.status() != "started":
                time.sleep(5)
                logger.loginfo("Waiting till " + self.name + " application starts")
            logger.loginfo("Application " + self.name + " started")

    def restart(self):
        self.stop()
        while self.isready() != "true":
            print "Waiting till app " + self.name + " stops"
            time.sleep(5)
        self.start()
        while self.isready() != "false":
            print "Waiting till app " + self.name + " starts"
            time.sleep(5)

    def update(self, distrpath):
        logger.loginfo("Try to uninstal " + self.name + " application")
        AdminApp.uninstall(self.name)
        logger.loginfo("App " + self.name + " uninstalled successfully")
        logger.loginfo("Try to install " + self.name + " application " + " from path " + distrpath)
        if self.cluster['name'] != "None":
            logger.loginfo("Install to " + self.cluster['name'])
            opts = "[" + \
                   "-cluster " + self.cluster['name'] + " " + \
                   "-appname " + self.name + " " + \
                   "-validateinstall warn" + " " + \
                   "-CtxRootForWebMod [[ .* .* " + self.contextroot + "]] " + \
                   "-MapWebModToVH [[.* .* default_host]]" + \
                   "]"
            AdminApp.install(distrpath, opts)
        else:
            for server in self.servers:
                logger.logseparator()
                logger.loginfo("Install to " + server['name'])
                opts = "[" + \
                       "-node " + server['nodeName'] + " " + \
                       "-cell " + self.cell + " " + \
                       "-server " + server['name'] + " " + \
                       "-appname " + self.name + " " + \
                       "-validateinstall warn" + " " + \
                       "-CtxRootForWebMod [[ .* .* " + self.contextroot + "]] " + \
                       "-MapWebModToVH [[.* .* default_host]]" + \
                       "]"
                AdminApp.install(distrpath, opts)
        logger.loginfo("App " + self.name + " updated successfully ")

    def uninstall(self):
        AdminApp.uninstall(self.name)

'''
log4j configuration manage class
'''
class txtfile:
    def __init__(self, file):
        self.file = file

    def changevalue(self, fulltag, starttag, endtag, val):
        start = 'false'
        file = open(self.file, 'r').readlines()
        print starttag
        for i in range(0, len(file)-1):
            print file[i]
            if file[i].find(fulltag) != -1:
                start = 'true'
            if start == 'true' and file[i].find(starttag) != -1:
                print "Find tag is true"
                print "Find needed line: " + file[i]
                result = file[i][:file[i].find(starttag)+len(starttag)] + val + file[i][file[i].find(endtag):]
                print "Processed line: " + result
                file[i] = result
                break
        newfile = open(self.file, 'w')
        newfile.writelines(file)
        newfile.close()



'''
Script main methods:
save_and_sync() - saving conf and sync all active nodes
wsadmin_to_list(str) - splits str to list of str delimited by '\n' for Linux or '\r\n' for Windows
find_last_dist(path) - ищет самый новый дистрибутив
get_files(path, mask) - ищет в папке по маске и возвращает словарь в виде {дата_модификации: 'полный_путь_к_файлу', ...}
'''


def save_and_sync():
    AdminConfig.save()
    AdminNodeManagement.syncActiveNodes()


def wsadmin_to_list(s):
    result = []
    if len(s) > 0 and s[0] == '[' and s[-1] == ']':
        tmplist = s[1:-1].split(" ")
    else:
        tmplist = s.split(lineSeparator)  # splits for Windows or Linux
    for item in tmplist:
        if len(item) > 0:
            result.append(item)
    return result


def find_last_dist(p):
    files = get_files(p, 'ear')
    print files
    files.update(get_files(p, 'war'))
    return files[max(files.keys())]


def get_files(p, mask, files=None):
    if files is None:
        files = {}
    for item in os.listdir(p):
        fullname = os.path.join(p, item)
        if os.path.isdir(fullname):
            get_files(fullname, mask, files)
        else:
            if fullname.endswith(mask):
                filename = os.path.join(p, item)
                lastmodified = os.path.getmtime(filename)
                files[lastmodified] = filename
    return files


logger = Logger()
lineSeparator = jsys.getProperty('line.separator')
if len(sys.argv) < 3:
    logger.logerror("Wrong arguments quantity for update!\n"
                    "Minimal quantity is 3:\n"
                    "%SCRIPT% %OBJECT_TYPE% %WHAT_TO_DO% %OBJECT_NAME% [%OPT_1%...%OPT_N%]")
else:
    manageObjectType = sys.argv[0]
    whatToDo = sys.argv[1]
    manageObjectNames = sys.argv[2]

if manageObjectType.lower() == "application":
    appnames = manageObjectNames.split(',')
    applist = []
    for name in appnames:
        applist.append(Application(name))
    logger.logstartinfo("Obtained apps parameters:")
    for app in applist:
        logger.loginfo(app)
    if whatToDo.lower() == "update":
        if len(applist) != 1:
            logger.logerror("Cant update more than one application from one folder!")
        else:
            app = applist[0]
            if len(sys.argv) != 4:
                logger.logerror(
                    "Wrong arguments quantity for update!\n"
                    "Default signature is: %SCRIPT% application update %APP_NAME% %PATH_TO_NEW_DISTR%")
            else:
                path = find_last_dist(sys.argv[3])
                logger.loginfo(app.name + 'will be updated from path: ' + path)
                logger.logstartinfo("START WORK. TRYING TO UPDATE APPLICATION " + app.name)
                if app.status() == "started":
                    logger.loginfo("Application named " + app.name + " is running. Trying to stop it")
                    app.stop()
                    appWasStopped = 'false'
                else:
                    logger.loginfo("Application already stopped")
                    appWasStopped = 'true'
                logger.logseparator()
                logger.loginfo("Trying to update " + app.name)
                app.update(path)
                logger.loginfo("Application updated")
                logger.logseparator()
                logger.loginfo("Trying to start app")
                if not appWasStopped == 'true':
                    app.start()
                    logger.loginfo("Application " + app.name + " started")
                else:
                    logger.loginfo(app.name + " was not started. Don't need to start now. Waiting for better times")
                save_and_sync()
                logger.logendinfo()
    if whatToDo.lower() == "uninstall":
        if len(sys.argv) != 3:
            logger.logerror("Wrong arguments quantity for update!\n"
                            "Default signature is: %SCRIPT% application uninstall %APP_NAME(S)%")
        else:
            for app in applist:
                logger.logstartinfo("TRYING TO UNINSTALL APP(S)")
                if app.status() == "started":
                    logger.loginfo("Application named " + app.name + " is running. Trying to stop it before uninstall")
                    app.stop()
                else:
                    logger.loginfo("Application named " + app.name + " stopped. Trying to uninstall")
                app.uninstall()
                save_and_sync()
                logger.logseparator()
            logger.logendinfo()
    if whatToDo.lower() == "restart":
        logger.logstartinfo("TRYING TO RESTART APP(S)")
        for app in applist:
            if app.status() == "started":
                AdminControl.invoke(app.servers[0]['applicationManager'], 'stopApplication', app.name)
            while not (app.isready() == "true" or app.status() != "stopped"):
                time.sleep(5)
                logger.loginfo("Waiting till application " + app.name + " stops")
            logger.loginfo(app.name + " successfully stopped")
            logger.loginfo("")
        logger.logseparator()
        logger.loginfo("All applications stopped, now trying to start")
        for app in applist:
            logger.loginfo("Trying to start " + app.name)
            AdminControl.invoke(app.servers[0]['applicationManager'], 'startApplication', app.name)
            while app.isready() == "false" or app.status() == "stopped":
                time.sleep(5)
                logger.loginfo("Waiting till " + app + " starts")
            logger.loginfo(app.name + " successfully started")
        save_and_sync()
        logger.logendinfo()
    if whatToDo.lower() == "stop":
        logger.logstartinfo("TRYING TO STOP APP(S)")
        for app in applist:
            if app.status() == "started":
                app.stop()
            else:
                logger.loginfo(app.name + " already stopped")
            logger.loginfo("")
        logger.logseparator()
        logger.loginfo("All applications stopped")
    if whatToDo.lower() == "start":
        logger.logstartinfo("TRYING TO START APP(S)")
        for app in applist:
            if app.status() == "stopped":
                app.start()
            else:
                logger.loginfo(app.name + " already stopped")
            logger.loginfo("")
        logger.logseparator()
        logger.loginfo("All applications started")
elif manageObjectType.lower() == 'xml':
    xml = txtfile(manageObjectNames)
    if whatToDo.lower() == 'updateval':
        fulltag = sys.argv[3]
        starttag = sys.argv[4]
        endtag = sys.argv[5]
        value = sys.argv[6]
        xml.changevalue(fulltag, starttag, endtag, value)

elif manageObjectType.lower() == 'cluster':
    clusters = manageObjectNames.split(',')
    clusterlist = []
    for name in clusters:
        clusterlist.append(Cluster(name))
    print clusterlist
    if whatToDo.lower() == "stop":
        logger.logstartinfo("TRYING TO STOP CLUSTER(S)")
        for cluster in clusterlist:
            cluster.stop()
            logger.loginfo("")
        logger.logendinfo()
    if whatToDo.lower() == "start":
        logger.logstartinfo("TRYING TO START CLUSTER(S)")
        for cluster in clusterlist:
            cluster.start()
            logger.loginfo("")
        logger.logendinfo()
    if whatToDo.lower() == "restart":
        logger.logstartinfo("TRYING TO RESTART CLUSTER(S)")
        for cluster in clusterlist:
            cluster.restart()
            logger.loginfo("")
        logger.logendinfo()
else:
    logger.logerror("Can't apply passed arguments to script!\n"
                    "Please, set right parameters and try again")
