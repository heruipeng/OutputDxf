# Embedded file name: D:\genesis\sys\scripts\pylib\genClasses.py
_header = {'author': 'Mike J. Hopkins',
 'date': '03/15/2002',
 'revision': '1.1.4',
 'title': 'genClasses',
 'description': '\n\tThis module defines classes to be used with Genesis 2000\n\t'}
import os, sys, string, time

class Genesis:

    def __init__(self):
        self.prefix = '@%#%@'
        self.blank()
        self.normalize()
        self.pid = os.getpid()
        tmp = 'gen_' + `(self.pid)` + '.' + `(time.time())`
        if os.environ.has_key('GENESIS_TMP'):
            self.tmpfile = os.path.join(os.environ['GENESIS_TMP'], tmp)
        else:
            self.tmpfile = os.path.join('/tmp', tmp)

    def __del__(self):
        if os.path.isfile(self.tmpfile):
            res = os.unlink(self.tmpfile)
            if res:
                self.error('Error deleting tmpfile', res)

    def normalize(self):
        if not os.environ.has_key('GENESIS_DIR'):
            self.error('GENESIS_DIR not set', 1)
        self.gendir = os.environ['GENESIS_DIR']
        if not os.environ.has_key('GENESIS_EDIR'):
            self.error('GENESIS_EDIR not set', 1)
        self.edir = os.environ['GENESIS_EDIR']
        if not os.path.isdir(self.edir):
            self.edir = os.path.join(self.gendir, self.edir)
        if not os.path.isdir(self.edir):
            self.error('Cannot normalize GENESIS_EDIR', 1)
        return 0

    def blank(self):
        self.STATUS = None
        self.READANS = None
        self.COMANS = None
        self.PAUSANS = None
        self.MOUSEANS = None
        return

    def sendCmd(self, cmd, args = ''):
        self.blank()
        wsp = ' ' * (len(args) > 0)
        cmd = self.prefix + cmd + wsp + args + '\n'
        sys.stdout.write(cmd)
        sys.stdout.flush()
        return 0

    def error(self, msg, severity = 0):
        sys.stderr.write(msg + '\n')
        if severity:
            sys.exit(severity)

    def write(self, msg):
        sys.stdout.write(msg + '\n')

    def SU_ON(self):
        return self.sendCmd('SU_ON')

    def SU_OFF(self):
        return self.sendCmd('SU_OFF')

    def VON(self):
        return self.sendCmd('VON')

    def VOF(self):
        return self.sendCmd('VOF')

    def PAUSE(self, msg):
        self.sendCmd('PAUSE', msg)
        self.STATUS = string.atoi(raw_input())
        self.READANS = raw_input()
        self.PAUSANS = raw_input()
        return self.STATUS

    def MOUSE(self, msg, mode = 'p'):
        self.sendCmd('MOUSE ' + mode, msg)
        self.STATUS = string.atoi(raw_input())
        self.READANS = raw_input()
        self.MOUSEANS = raw_input()
        return self.STATUS

    def COM(self, args):
        self.sendCmd('COM', args)
        self.STATUS = string.atoi(raw_input())
        self.READANS = raw_input()
        self.COMANS = self.READANS[:]
        return self.STATUS

    def AUX(self, args):
        self.sendCmd('AUX', args)
        self.STATUS = string.atoi(raw_input())
        self.READANS = raw_input()
        self.COMANS = self.READANS[:]
        return self.STATUS

    def INFO(self, args):
        self.COM('info,out_file=%s,write_mode=replace,args=%s' % (self.tmpfile, args))
        lineList = open(self.tmpfile, 'r').readlines()
        os.unlink(self.tmpfile)
        return lineList

    def DO_INFO(self, args):
        self.COM('info,out_file=%s,write_mode=replace,args=%s' % (self.tmpfile, args))
        lineList = open(self.tmpfile, 'r').readlines()
        os.unlink(self.tmpfile)
        infoDict = self.parseInfo(lineList)
        return infoDict

    def dbutil(self, *args):
        binary = os.path.join(self.edir, 'misc', 'dbutil')
        args = string.join(args)
        fd = os.popen(binary + ' ' + args)
        res = fd.readlines()
        return res

    def convertToNumber(self, value):
        try:
            return string.atoi(value)
        except:
            try:
                return string.atof(value)
            except:
                return value

    def parseInfo(self, infoList):
        dict = {}
        for line in infoList:
            ss = string.split(line, ' = ', 1)
            if len(ss) == 2:
                key = string.strip(ss[0])[4:]
                val = string.strip(ss[1])
                valList = string.split(val, "'")
                if '(' in val:
                    dict[key] = []
                    for n in range(len(valList)):
                        if n % 2 == 1:
                            dict[key].append(self.convertToNumber(valList[n]))

                elif len(valList) == 3:
                    dict[key] = self.convertToNumber(string.split(val, "'")[1])
                elif len(valList) == 1:
                    dict[key] = self.convertToNumber(string.split(val, "'")[0])

        return dict


class Job(Genesis):

    def __init__(self, name):
        self.name = name
        Genesis.__init__(self)

    def __getattr__(self, name):
        print 'Dynamically fetching attribute::', name
        if name == 'matrix':
            self.matrix = Matrix(self)
            return self.matrix
        elif name == 'info':
            self.info = self.getInfo()
            return self.info
        elif name == 'steps':
            self.steps = self.getSteps()
            return self.steps
        elif name == 'forms':
            self.forms = self.getForms()
            return self.forms
        elif name == 'db':
            self.db = self.dbName()
            return self.db
        elif name == 'dbpath':
            self.dbpath = self.dbPath()
            return self.dbpath
        elif name == 'lockStat':
            self.lockStat = self.dbStat()
            return self.lockStat
        elif name == 'user':
            self.user = self.getUser()
            return self.user
        else:
            val = self.getGenesisAttr(name)
            return val

    def getInfo(self):
        self.info = self.DO_INFO('-t job -e ' + self.name)
        return self.info

    def getSteps(self):
        self.steps = {}
        for step in self.info['gSTEPS_LIST']:
            self.steps[step] = Step(self, step)

        return self.steps

    def getForms(self):
        self.forms = {}
        for form in self.info['gFORMS_LIST']:
            self.forms[form] = Form(self, form)

        return self.forms

    def dbName(self):
        res = self.dbutil('list', 'jobs', self.name)
        self.db = string.split(res[0])[3]
        return self.db

    def dbPath(self):
        res = self.dbutil('path', 'jobs', self.name)
        self.dbpath = string.strip(res[0])
        return self.dbpath

    def dbStat(self):
        res = self.dbutil('lock', 'test', self.name)
        ss = string.split(res[0])
        d = {'no': 0,
         'yes': 1}
        self.lockStat = d[ss[0]]
        if len(ss) > 1:
            self.lockUser = ss[1]
        return self.lockStat

    def getUser(self):
        self.COM('get_user_name')
        self.user = self.COMANS
        return self.user

    def getGenesisAttr(self, name):
        for x in xrange(len(self.info['gATTRname'])):
            if self.info['gATTRname'][x] == name:
                return self.info['gATTRval'][x]
            if self.info['gATTRname'][x] == '.' + name:
                return self.info['gATTRval'][x]

        return None

    def setGenesisAttr(self, name, value):
        if name not in self.info['gATTRname']:
            return 0
        cmd = 'set_attribute,type=job,job=' + self.name
        cmd = cmd + ',name1=,name2=,name3='
        cmd = cmd + ',attribute=' + name + ',value='
        try:
            cmd = cmd + value
        except:
            cmd = cmd + `value`

        self.COM(cmd)
        return self.STATUS

    def open(self, lock = 0):
        self.COM('open_job,job=' + self.name)
        if lock and not self.lockStat:
            self.checkout()

    def close(self, unlock = 0):
        self.COM('close_job,job=' + self.name)
        if unlock and self.lockStat:
            self.checkin()

    def checkout(self):
        self.COM('check_inout,mode=out,type=job,job=' + self.name)
        self.lockStat = 1
        self.lockUser = self.user
        return self.STATUS

    def checkin(self):
        self.COM('check_inout,mode=in,type=job,job=' + self.name)
        self.lockStat = 0
        return self.STATUS

    def save(self):
        self.COM('save_job,job=' + self.name + ',override=no')
        return self.STATUS

    def removeStep(self, name):
        stat = self.COM('delete_entity,job=' + self.name + ',type=step,name=' + name)
        delattr(self, 'steps')
        return stat

    def addStep(self, name):
        self.COM('create_entity,job=' + self.name + ',is_fw=no,type=step,name=' + name + ',db=')
        self.steps[name] = Step(self, name)
        return self.STATUS


class Step(Genesis):

    def __init__(self, job, name):
        Genesis.__init__(self)
        self.job = job
        self.name = name
        self.group = None
        return

    def COM(self, args):
        if self.group:
            self.setGroup()
        self.sendCmd('COM', args)
        self.STATUS = string.atoi(raw_input())
        self.READANS = raw_input()
        self.COMANS = self.READANS[:]
        return self.STATUS

    def __getattr__(self, name):
        print 'Dynamically fetching Step attribute::', name
        if name == 'info':
            self.info = self.getInfo()
            return self.info
        elif name == 'profile':
            self.profile = self.getProfile()
            return self.profile
        elif name == 'layers':
            self.layers = self.getLayers()
            return self.layers
        elif name == 'sr':
            self.sr = self.getSr()
            return self.sr
        else:
            val = self.getGenesisAttr(name)
            return val

    def getInfo(self):
        self.info = self.DO_INFO('-t step -e ' + self.job.name + '/' + self.name)
        return self.info

    def getProfile(self):
        self.profile = Empty()
        self.profile.xmin = self.info['gPROF_LIMITSxmin']
        self.profile.ymin = self.info['gPROF_LIMITSymin']
        self.profile.xmax = self.info['gPROF_LIMITSxmax']
        self.profile.ymax = self.info['gPROF_LIMITSymax']
        self.profile.xsize = self.profile.xmax - self.profile.xmin
        self.profile.ysize = self.profile.ymax - self.profile.ymin
        self.profile.xcenter = self.profile.xmin + self.profile.xsize / 2
        self.profile.ycenter = self.profile.ymin + self.profile.ysize / 2
        return self.profile

    def getSr(self):
        self.sr = Empty()
        self.sr.xmin = self.info['gSR_LIMITSxmin']
        self.sr.ymin = self.info['gSR_LIMITSymin']
        self.sr.xmax = self.info['gSR_LIMITSxmax']
        self.sr.ymax = self.info['gSR_LIMITSymax']
        self.sr.eBorder = self.profile.xmax - self.sr.xmax
        self.sr.wBorder = self.sr.xmin - self.profile.xmin
        self.sr.nBorder = self.profile.ymax - self.sr.ymax
        self.sr.sBorder = self.sr.ymin - self.profile.ymin
        self.sr.table = []
        for x in xrange(len(self.info['gSRstep'])):
            d = Empty()
            d.step = self.info['gSRstep'][x]
            d.xanchor = self.info['gSRxa'][x]
            d.yanchor = self.info['gSRya'][x]
            d.xdist = self.info['gSRdx'][x]
            d.ydist = self.info['gSRdy'][x]
            d.xnum = self.info['gSRnx'][x]
            d.ynum = self.info['gSRny'][x]
            d.angle = self.info['gSRangle'][x]
            d.mirror = self.info['gSRmirror'][x]
            d.xmin = self.info['gSRxmin'][x]
            d.ymin = self.info['gSRymin'][x]
            d.xmax = self.info['gSRxmax'][x]
            d.ymax = self.info['gSRymax'][x]
            self.sr.table.append(d)

        return self.sr

    def getLayers(self):
        self.layers = []
        for layName in self.info['gLAYERS_LIST']:
            lay = Layer(self, layName)
            self.layers.append(lay)

        return self.layers

    def getGenesisAttr(self, name):
        for x in xrange(len(self.info['gATTRname'])):
            if self.info['gATTRname'][x] == name:
                return self.info['gATTRval'][x]
            if self.info['gATTRname'][x] == '.' + name:
                return self.info['gATTRval'][x]

        return None

    def setGenesisAttr(self, name, value):
        if name not in self.info['gATTRname']:
            return 0
        cmd = 'set_attribute,type=step,job=' + self.job.name
        cmd = cmd + ',name1=' + self.name + ',name2=,name3='
        cmd = cmd + ',attribute=' + name + ',value='
        try:
            cmd = cmd + value
        except:
            cmd = cmd + `value`

        self.COM(cmd)
        return self.STATUS

    def open(self, iconic = 'No'):
        STR = 'open_entity,job=%s,type=step,name=%s,iconic=%s' % (self.job.name, self.name, iconic)
        self.COM(STR)
        self.group = self.COMANS
        return self.STATUS

    def setGroup(self):
        self.AUX('set_group,group=' + self.group)

    def close(self):
        self.setGroup()
        self.COM('editor_page_close')

    def selectRectangle(self, xs, ys, xe, ye, intersect = 'no'):
        self.setGroup()
        self.resetFilter()
        self.COM('filter_area_strt')
        self.COM('filter_area_xy,x=' + `xs` + ',y=' + `ys`)
        self.COM('filter_area_xy,x=' + `xe` + ',y=' + `ye`)
        self.COM('filter_area_end,layer=,filter_name=popup,operation=select,area_type=rectangle,inside_area=yes,intersect_area=' + intersect)
        return self.READANS

    def getSubSteps(self, step = None, stepList = []):
        if step == None:
            step = self.name
        stepDict = self.DO_INFO(' -t step -d SR -e %s/%s' % (self.job.name, step))
        for step in stepDict['gSRstep']:
            if step not in stepList:
                self.getSubSteps(step, stepList)
                stepList.append(step)

        return stepList


class Layer:

    def __init__(self, step, name):
        self.step = step
        self.name = name
        self.job = self.step.job

    def __getattr__(self, name):
        if name == 'info':
            self.info = self.getInfo()
            return self.info
        else:
            val = self.getGenesisAttr(name)
            return val

    def getInfo(self):
        STR = ' -t layer -e %s/%s/%s' % (self.job.name, self.step.name, self.name)
        self.info = self.step.DO_INFO(STR)
        return self.info

    def getGenesisAttr(self, name):
        for x in xrange(len(self.info['gATTRname'])):
            if self.info['gATTRname'][x] == name:
                return self.info['gATTRval'][x]
            if self.info['gATTRname'][x] == '.' + name:
                return self.info['gATTRval'][x]

        return None

    def setGenesisAttr(self, name, value):
        if name not in self.info['gATTRname']:
            return 0
        cmd = 'set_attribute,type=layer,job=' + self.job.name
        cmd = cmd + ',name1=' + self.step.name + ',name2=' + self.name + ',name3='
        cmd = cmd + ',attribute=' + name + ',value='
        try:
            cmd = cmd + value
        except:
            cmd = cmd + `value`

        self.step.COM(cmd)
        return self.STATUS


class Empty:

    def __init__(self):
        pass