# Embedded file name: D:\genesis\sys\scripts\pylib\genCommands.py
_HEADER = {'AUTHOR': 'Mike J. Hopkins',
 'PACKAGE': 'Genesis-Python Interface',
 'REV': '1.1.6',
 'DATE': '05/20/2002',
 'MODULE': 'genCommands.py',
 'MODULE REV': '1.1.6',
 'MODULE DATE': '05/20/2002',
 'DESCRIPTION': '\n\tThis module defines commands to be used with Genesis 2000\n\t'}
import string

class Generic:

    def __init__(self, parent):
        self.parent = parent

    def COM(self, cmd):
        self.parent.COM(cmd)
        self.COMANS = self.parent.COMANS
        self.READANS = self.parent.READANS
        self.STATUS = self.parent.STATUS
        return self.STATUS


class Job(Generic):

    def __init__(self, parent):
        self.parent = parent
        self.name = self.parent.name

    def open(self, lock = 0):
        self.COM('open_job,job=' + self.name)
        if lock and not self.parent.lockStat:
            self.checkout()

    def close(self, unlock = 0):
        self.COM('close_job,job=' + self.name)
        if unlock and self.parent.lockStat:
            self.checkin()

    def checkout(self):
        self.COM('check_inout,mode=out,type=job,job=' + self.name)
        self.parent.lockStat = 1
        self.parent.lockUser = self.parent.user
        return self.STATUS

    def checkin(self):
        self.COM('check_inout,mode=in,type=job,job=' + self.name)
        self.parent.lockStat = 0
        return self.STATUS

    def save(self):
        self.COM('save_job,job=' + self.name + ',override=no')
        return self.STATUS

    def removeStep(self, name):
        self.COM('delete_entity,job=' + self.name + ',type=step,name=' + name)
        self.parent._forceRefresh()
        return self.STATUS

    def addStep(self, name):
        self.COM('create_entity,job=' + self.name + ',is_fw=no,type=step,name=' + name + ',db=')
        self.parent._forceRefresh()
        return self.STATUS

    def setGenesisAttr(self, name, value):
        if name not in self.parent.info['gATTRname']:
            return 0
        cmd = 'set_attribute,type=job,job=' + self.name
        cmd = cmd + ',name1=,name2=,name3='
        cmd = cmd + ',attribute=' + name + ',value='
        try:
            cmd = cmd + value
        except:
            cmd = cmd + `value`

        self.COM(cmd)
        self.parent._deleteAttribute('info')
        return self.STATUS


class Step(Generic):

    def __init__(self, parent):
        self.parent = parent
        self.name = self.parent.name
        self.job = self.parent.job

    def open(self, iconic = 'No'):
        STR = 'open_entity,job=%s,type=step,name=%s,iconic=%s' % (self.job.name, self.name, iconic)
        self.COM(STR)
        self.parent.group = self.COMANS
        return self.STATUS

    def close(self):
        self.COM('editor_page_close')

    def clearAll(self):
        self.COM('clear_layers')
        self.COM('affected_layer,name=,mode=all,affected=no')

    def display(self, lay, work = 1):
        self.display_layer(lay, 1, work)

    def display_layer(self, lay, num, work = 0, display = 'yes'):
        self.COM('display_layer,name=' + lay + ',display=' + display + ',number=' + `num`)
        if work:
            self.COM('work_layer,name=' + lay)

    def affect(self, lay):
        self.COM('affected_layer,name=' + lay + ',mode=single,affected=yes')

    def unaffect(self, lay, mode = 'single'):
        self.COM('affected_layer,name=' + lay + ',mode=' + mode + ',affected=no')

    def affectFilter(self, filter):
        self.COM('affected_filter,filter=' + filter)
        self.COM('get_affect_layer')
        return string.split(self.COMANS)

    def resetFilter(self):
        self.COM('filter_reset,filter_name=popup')

    def setAttrFilter(self, attr, text = ''):
        self.COM('filter_atr_set,filter_name=popup,condition=yes,attribute=' + attr + ',text=' + `text`)

    def setSymbolFilter(self, syms):
        self.COM('filter_set,filter_name=popup,update_popup=no,include_syms=' + syms)

    def setFeatureFilter(self, feat = 'line\\;pad\\;surface\\;arc\\;text'):
        self.COM('filter_set,filter_name=popup,update_popup=no,feat_types=' + feat)

    def setPolarityFilter(self, polarity = 'positive'):
        self.COM('filter_set,filter_name=popup,update_popup=no,polarity=' + polarity)

    def selectRectangle(self, xs, ys, xe, ye, intersect = 'no'):
        self.resetFilter()
        self.COM('filter_area_strt')
        self.COM('filter_area_xy,x=' + `xs` + ',y=' + `ys`)
        self.COM('filter_area_xy,x=' + `xe` + ',y=' + `ye`)
        self.COM('filter_area_end,layer=,filter_name=popup,operation=select,area_type=rectangle,inside_area=yes,intersect_area=' + intersect)
        return string.atoi(self.COMANS)

    def refSelectFilter(self, refLay, include_syms = '', exclude_syms = '', mode = 'touch'):
        STR = 'sel_ref_feat,layers=%s,use=filter,mode=%s,\t\tf_types=line\\;pad\\;surface\\;arc\\;text,polarity=positive\\;negative,\t\tinclude_syms=%s,exclude_syms=%s'
        STR = STR % (refLay,
         mode,
         include_syms,
         exclude_syms)
        self.COM(STR)
        return string.atoi(self.COMANS)

    def copyToAffected(self, invert = 'no', dx = 0, dy = 0, size = 0):
        STR = 'sel_copy_other,dest=affected_layers,invert=%s,dx=%f,dy=%f,size=%f'
        STR = STR % (invert,
         dx,
         dy,
         size)
        self.COM(STR)

    def copyToLayer(self, lay, invert = 'no', dx = 0, dy = 0, size = 0):
        STR = 'sel_copy_other,dest=layer_name,target_layer=%s,invert=%s,dx=%f,dy=%f,size=%f'
        STR = STR % (lay,
         invert,
         dx,
         dy,
         size)
        self.COM(STR)

    def createLayer(self, name, context = 'misc', type = 'document', polarity = 'positive'):
        STR = 'create_layer,layer=%s,context=%s,type=%s,polarity=%s' % (name,
         context,
         type,
         polarity)
        self.COM(STR)
        self.parent._forceRefresh()

    def removeLayer(self, lay):
        self.COM('delete_layer,layer=' + lay)
        self.parent._forceRefresh()

    def copyLayer(self, job, step, lay, dest_lay, mode = 'replace'):
        STR = 'copy_layer,source_job=%s,source_step=%s,source_layer=%s,dest=layer_name,dest_layer=%s,mode=%s'
        STR = STR % (job,
         step,
         lay,
         dest_lay,
         mode)
        self.COM(STR)
        self.parent._forceRefresh()

    def setGenesisAttr(self, name, value):
        if name not in self.parent.info['gATTRname']:
            return 0
        cmd = 'set_attribute,type=step,job=' + self.job.name
        cmd = cmd + ',name1=' + self.name + ',name2=,name3='
        cmd = cmd + ',attribute=' + name + ',value='
        try:
            cmd = cmd + value
        except:
            cmd = cmd + `value`

        self.COM(cmd)
        self.parent._deleteAttribute('info')
        return self.STATUS


class Matrix(Generic):

    def __init__(self, parent):
        self.parent = parent
        self.name = self.parent.name
        self.job = self.parent.job

    def removeLayer(self, lay):
        true = 0
        for x in xrange(len(self.parent.info['gROWname'])):
            if self.parent.info['gROWname'][x] == lay:
                true = 1
                break

        if true:
            self.COM('matrix_delete_row,job=%s,matrix=matrix,row=%s' % (self.job.name, x + 1))
            self.parent._forceRefresh()
            return self.STATUS

    def addLayer(self, name, index, context = 'board', type = 'signal', polarity = 'positive'):
        self.COM('matrix_insert_row,job=' + self.job.name + ',matrix=matrix,row=' + `index`)
        STR = 'matrix_add_layer,job=%s,matrix=matrix,layer=%s,row=%i,context=%s,type=%s,polarity=%s' % (self.job.name,
         name,
         index,
         context,
         type,
         polarity)
        self.COM(STR)
        self.parent._forceRefresh()
        return self.STATUS


class Layer(Generic):

    def __init__(self, parent):
        self.parent = parent
        self.name = self.parent.name
        self.step = self.parent.step
        self.job = self.parent.job

    def COM(self, cmd):
        self.step.COM(cmd)
        self.COMANS = self.step.COMANS
        self.READANS = self.step.READANS
        self.STATUS = self.step.STATUS
        return self.step.STATUS

    def setGenesisAttr(self, name, value):
        if name not in self.parent.info['gATTRname']:
            return 0
        cmd = 'set_attribute,type=layer,job=' + self.job.name
        cmd = cmd + ',name1=' + self.step.name + ',name2=' + self.name + ',name3='
        cmd = cmd + ',attribute=' + name + ',value='
        try:
            cmd = cmd + value
        except:
            cmd = cmd + `value`

        self.COM(cmd)
        self.parent._deleteAttribute('info')
        return self.STATUS