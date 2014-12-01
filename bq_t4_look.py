#!/usr/bin/env python

"""
bq_t4_look.py

Created by Mikolaj Szydlarski on 2014-04-29.
Copyright (c) 2014, ITA UiO - All rights reserved.
"""

import os
import sys
import datetime
import getopt

import numpy as np

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.ticker as ticker

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar

from PyQt4 import QtGui
from PyQt4 import Qt

from matplotlib import cm
from scipy.io.idl import readsav
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.image import NonUniformImage

plt.style.use('dark_background')
sys.path.append("./bq_t4_sys/")
sys.path.append("./bq_t4_sys/cstagger/")

import bifrost


first_file_name  = "no_file"
first_slice      = -1
first_depth      = -1000.0
help_message     = '''

    ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    :: Python/Qt4 based quick look tool app for Bifrost cubes ::
    ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
    
     You can setup some parameters from command line:

     -i / --input  - point to the snap file
     -s / --slice  - jump directly to cube[:,:,slice]
     -z / --depth  - finds a slice to the corresponding depth 
                     val provided in real [mM] coordinates
     -h / --help   - print this help msg
    
    ............................................................

'''

def process_file_name(file_name):
   a = os.path.splitext(file_name)[0]
   a = a.split("/")[:-1]
   a.append(" ")
   where_str = "/".join(a)
   b = os.path.splitext(file_name)[0]
   b = b.split("/")[-1]
   b = b.split("_")
   base_name = "_".join(b[0:-1])
   snap_n    = b[-1]
   return where_str.strip(), base_name.strip(), snap_n.strip()

def z2indx(z_vec, z):
    return np.argmax( z_vec >= z )

def get_bifrost_param(file_name, offset):
    where_str, base_name, snap_n = process_file_name(file_name)
    return bifrost.read_idl_ascii(where_str + base_name + ('_%s' % str(int(snap_n) + offset)) + '.idl')

def get_bifrost_obj(file_name, offset, with_no_aux):
    where_str, base_name, snap_n = process_file_name(file_name)
    print '[Processing] : ' ,base_name, " snap No: ", int(snap_n) + offset, " in ", where_str
    formater = "_%%0%ii" % len(str(int(snap_n) + offset))
    return bifrost.OSC_data(int(snap_n) + offset, template = where_str + base_name + formater, meshfile = where_str + base_name + ".mesh", no_aux=with_no_aux), base_name, int(snap_n) + offset

class Window(QtGui.QDialog):
    def __init__(self, parent=None):

        super(Window, self).__init__(parent)

        self.setAcceptDrops(True)
        self.figure = plt.figure()

        # --- Just for fun lets start with nice picture

        img = mpimg.imread('./bq_t4_sys/thor.png')
        ax = plt.Axes(self.figure,[0.,0.,1.,1.])
        ax.set_axis_off()
        self.figure.add_axes(ax)
        plt.imshow(img,cmap=cm.get_cmap('gray'))

        # ---------------------------------------------

        self.canvas = FigureCanvas(self.figure)

        # ---------------------------------------------

        self.toolbar = NavigationToolbar(self.canvas, self)

        # ---------------------------------------------

        self.slider = QtGui.QSlider(orientation=Qt.Qt.Horizontal)
        self.slider.setTickInterval(1)
        self.slider.valueChanged.connect(self.plot)

        # ----------------------------------------------
        
        self.view_combo = QtGui.QComboBox(self)
        self.view_combo.activated[str].connect(self.changeView)
        self.view_combo.addItem('X-Y')
        self.view_combo.addItem('X-Z')
        self.view_combo.addItem('Y-Z')
        self.view = 'X-Y'
        self.slide_dimension = 2 # will slide by default though z

        self.combo = QtGui.QComboBox(self)
        self.combo.activated[str].connect(self.comboActivated)

        # -- check box 

        self.hbox = QtGui.QHBoxLayout()
        # self.hbox.addStretch(1)

        self.back_button = QtGui.QPushButton('<',self)
        self.back_button.clicked.connect(self.goBack)
        self.next_button = QtGui.QPushButton('>',self)
        self.next_button.clicked.connect(self.goNext)

        self.check_abs = QtGui.QCheckBox('Absolute')
        # self.check_abs.toggle()
        self.check_abs.stateChanged.connect(self.plot)

        self.check_bw = QtGui.QCheckBox('B&W')
        # self.check_bw.toggle()
        self.check_bw.stateChanged.connect(self.plot)

        self.check_log = QtGui.QCheckBox('Log')
        # self.check_log.toggle()
        self.check_log.stateChanged.connect(self.plot)


        self.check_si = QtGui.QCheckBox('CGS Units')
        self.check_si.toggle()
        self.check_si.stateChanged.connect(self.plot)

        self.check_aux = QtGui.QCheckBox('No AUX')
        self.check_aux.toggle()
        self.check_aux.stateChanged.connect(self.reset_bifrost_obj)

        self.hbox.addWidget(self.check_si)
        self.hbox.addWidget(self.check_abs)
        self.hbox.addWidget(self.check_log)
        self.hbox.addWidget(self.check_bw)
        self.hbox.addWidget(self.check_aux)
        self.hbox.addWidget(self.back_button)
        self.hbox.addWidget(self.next_button)
        self.hbox.addWidget(self.combo)
        self.hbox.addWidget(self.view_combo)

        # set the layout
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addLayout(self.hbox)
        layout.addWidget(self.canvas)
        layout.addWidget(self.slider)
        self.setLayout(layout)

        # actual data stuff
        self.fpath = first_file_name

        # self.data = np.einsum('ijk->kji', self.data)

        self.tag = 'r'

        if (first_file_name != "no_file"):
            self.param = get_bifrost_param(self.fpath,0)
            self.b, self.base_name, self.snap_n = get_bifrost_obj(self.fpath,0, self.check_aux.isChecked())
            self.data = self.b.getvar(self.tag)
            self.slide_dimension = 2
            self.slider.setMinimum(0)
            self.slider.setMaximum(self.data.shape[self.slide_dimension]-1)

            if (first_slice != -1):
                self.slider.setValue(first_slice)

            if (first_depth != -1000.0):
                self.slider.setValue(np.argmax( self.b.z >= first_depth ))

            if self.slider.value() >= self.data.shape[self.slide_dimension]:
                self.slider.setValue(self.data.shape[self.slide_dimension]-1)
            elif self.slider.value() < 0:
                self.slider.setValue(0)

            self.setCombo()
            self.plot()
        else:
            print "\t[!] Drag & Drop a snap file to plot its content"


    def keyPressEvent(self, event):
        
        key = event.key

        if key == Qt.Qt.Key_Right:
            self.slider.setValue(self.slider.value() + 1)
        elif key == Qt.Qt.Key_Left:
            self.slider.setValue(self.slider.value() - 1)

    def goBack(self):
        self.param = get_bifrost_param(self.fpath,-1)
        self.b, self.base_name, self.snap_n = get_bifrost_obj(self.fpath,-1, self.check_aux.isChecked())
        self.get_data()
        self.plot()
        where_str, base_name, snap_n = process_file_name(self.fpath)
        snap_n = str(int(snap_n) - 1)
        self.fpath = where_str + base_name + '_' + snap_n + '.snap'
        pass

    def goNext(self):
        self.param = get_bifrost_param(self.fpath,1)
        self.b, self.base_name, self.snap_n = get_bifrost_obj(self.fpath,1,self.check_aux.isChecked())
        self.get_data()
        self.plot()
        where_str, base_name, snap_n = process_file_name(self.fpath)
        snap_n = str(int(snap_n) + 1)
        self.fpath = where_str + base_name + '_' + snap_n + '.snap'
        pass

    def setCombo(self):
        self.combo.clear()
        for tag in self.b.snapvars:
            self.combo.addItem(tag)
        if not self.check_aux.isChecked():
            for tag in self.b.auxvars:
                self.combo.addItem(tag)
    
    def changeView(self, text):
        self.view = text
        self.get_data()
        self.plot()
        print 'View changed to: ', self.view

    def comboActivated(self, text):
        self.tag = text
        self.data = self.b.getvar(self.tag)
        self.plot()

    def reset_bifrost_obj(self):
        self.b, self.base_name, self.snap_n = get_bifrost_obj(self.fpath,0,self.check_aux.isChecked())
        print self.b.snapvars
        self.get_data()

    def get_data(self):
        self.data = self.b.getvar(self.tag)
        if self.view == 'X-Y':
            self.slide_dimension = 2
        elif self.view == 'X-Z':
            self.slide_dimension = 1
        elif self.view == 'Y-Z':
            self.slide_dimension = 0

        self.slider.setMinimum(0)
        self.slider.setMaximum(self.data.shape[self.slide_dimension]-1)

        if self.slider.value() >= self.data.shape[self.slide_dimension]:
            self.slider.setValue(self.data.shape[self.slide_dimension]-1)
        elif self.slider.value() < 0:
            self.slider.setValue(0)

        self.setCombo()

    def home(self):
        self.toolbar.home()
    def zoom(self):
        self.toolbar.zoom()
    def pan(self):
        self.toolbar.pan()

    def plot(self):
        plt.clf()
        ax = self.figure.add_subplot(111)
        slice_str = '[?]'
        # extension = []
        if self.view == 'X-Y':
            image = self.data[:,:,self.slider.value()]
            slice_str = 'z = %f ' % self.b.z[self.slider.value()]
            ax.set_ylabel('y-direction')
            ax.set_xlabel('x-direction')
            # extension = [0, self.param['mx'], 0, self.param['my']]
        elif self.view == 'X-Z':
            image = self.data[:,self.slider.value(),:]
            slice_str = 'y = %f ' % self.b.y[self.slider.value()]
            ax.set_ylabel('z-direction')
            ax.set_xlabel('x-direction')
            # extension = [0, self.param['mx'], 0, self.param['mz']]
        elif self.view == 'Y-Z':
            image = self.data[self.slider.value(),:,:]
            slice_str = 'x = %f ' % self.b.x[self.slider.value()]
            ax.set_ylabel('z-direction')
            ax.set_xlabel('y-direction')
            # extension = [0, self.param['my'], 0, self.param['mz']]
        # image = np.fliplr(image)
        # image = np.rot90(image,k=3)
        
        label = "Value"
        color = cm.get_cmap('jet')
        
        ax.set_title("[%s] %s (Snap: %s) for %s \n[time: %s]" % (self.tag, self.base_name, self.snap_n, slice_str, str(datetime.timedelta(seconds=self.param['t']*self.param['u_t']))))
        # ax.xaxis.set_major_locator(ticker.MultipleLocator(int(64)))
        # ax.yaxis.set_major_locator(ticker.MultipleLocator(int(64)))
        
        if self.check_si.isChecked():
            
            if self.tag == 'r':
                image = image * self.param['u_r']
                unit_label = "[g/cm3]"
                label = "Value %s" % unit_label
            elif (self.tag == 'bx' or self.tag == 'by' or self.tag == 'bz'):
                image = image * self.param['u_b']
                unit_label = "[G]"
                label = "Value %s" % unit_label
            elif (self.tag == 'px' or self.tag == 'py' or self.tag == 'pz'):
                image = image * self.param['u_p']
                unit_label = "[Ba]"
                label = "Value %s" % unit_label
            elif self.tag == 'e':
                image = image * self.param['u_e']
                unit_label = "[erg]"
                label = "Value %s" % unit_label

        if self.check_abs.isChecked():
            image = np.absolute(image)
            label = "ABS( %s )" % label
        
        if self.check_log.isChecked():
            image = np.log10(image)
            label = "Log10( %s )" % label
        if self.check_bw.isChecked():
            # color = cm.get_cmap('gist_yarg')
            color = cm.get_cmap('Greys_r') # Mats favorite color palette 
            
        if self.view == 'X-Y':
            ax.set_ylabel('y-direction [Mm]')
            ax.set_xlabel('x-direction [Mm]')
            im = NonUniformImage(ax, interpolation='bilinear', extent=(self.b.x.min(),self.b.x.max(),self.b.y.min(),self.b.y.max()), cmap=color)
            im.set_data(self.b.x, self.b.y, np.fliplr(zip(*image[::-1])))
            ax.images.append(im)
            ax.set_xlim(self.b.x.min(),self.b.x.max())
            ax.set_ylim(self.b.y.min(),self.b.y.max())
            ax.xaxis.set_major_locator(ticker.MultipleLocator(int(4)))
            ax.yaxis.set_major_locator(ticker.MultipleLocator(int(4)))
        elif self.view == 'X-Z':
            ax.set_ylabel('z-direction [Mm]')
            ax.set_xlabel('x-direction [Mm]')
            im = NonUniformImage(ax, interpolation='bilinear', extent=(self.b.x.min(),self.b.x.max(),self.b.z.min(),self.b.z.max()), cmap=color)
            im.set_data(self.b.x, self.b.z[::-1], np.flipud(np.fliplr(zip(*image[::-1]))))
            ax.images.append(im)
            ax.set_xlim(self.b.x.min(),self.b.x.max())
            ax.set_ylim(self.b.z.max(),self.b.z.min())
            ax.xaxis.set_major_locator(ticker.MultipleLocator(int(4)))
            ax.yaxis.set_major_locator(ticker.MultipleLocator(int(2)))
        elif self.view == 'Y-Z':
            ax.set_ylabel('z-direction [Mm]')
            ax.set_xlabel('y-direction [Mm]')
            im = NonUniformImage(ax, interpolation='bilinear', extent=(self.b.y.min(),self.b.y.max(),self.b.z.min(),self.b.z.max()), cmap=color)
            im.set_data(self.b.y, self.b.z[::-1], np.flipud(np.fliplr(zip(*image[::-1]))))
            ax.images.append(im)
            ax.set_xlim(self.b.y.min(),self.b.y.max())
            ax.set_ylim(self.b.z.max(),self.b.z.min())
            ax.xaxis.set_major_locator(ticker.MultipleLocator(int(4)))
            ax.yaxis.set_major_locator(ticker.MultipleLocator(int(2)))
        # im = ax.imshow(image, interpolation='none', origin='lower', cmap=color, extent=extension)
        # ax.text(0.025, 0.025, (r'$\langle  B_{z}  \rangle = %2.2e$'+'\n'+r'$\langle |B_{z}| \rangle = %2.2e$') % (np.average(img),np.average(np.absolute(img))), ha='left', va='bottom', transform=ax.transAxes)
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        plt.colorbar(im, cax=cax,label=label)
        self.canvas.draw()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile().toLocal8Bit().data()
        if os.path.isfile(path):
            self.fpath = path
            self.param = get_bifrost_param(self.fpath,0)
            self.b, self.base_name, self.snap_n = get_bifrost_obj(self.fpath,0, self.check_aux.isChecked())
            self.get_data()
            self.plot()

def main(argv=None):

    global first_file_name
    global first_slice
    global first_depth
    
    if argv is None:
        argv = sys.argv

    opts, args = getopt.getopt(argv[1:], "hi:s:z:", ["help","input=","slice=","depth="])
        
    # option processing
    for option, value in opts:
        if option in ("-h", "--help"):
            print help_message
            return 0
        if option in ("-i", "--input"):
            first_file_name = value
            print '[Input file] : ', first_file_name
        if option in ("-s", "--slice"):
            first_slice = int(value)
        if option in ("-z", "--depth"):
            first_depth = float(value)
    print help_message

    app = QtGui.QApplication(sys.argv)
    main = Window()
    main.setWindowTitle('Bifrost Q(t4)uick Look App')
    main.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    sys.exit(main())
