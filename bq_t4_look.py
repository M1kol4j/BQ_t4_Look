import os
import sys
sys.setrecursionlimit(10000)
import datetime

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

first_file_name  = "big_nope"

plt.style.use('dark_background')
sys.path.append("./bq_t4_sys/")
sys.path.append("./bq_t4_sys/cstagger/")

import bifrost

def process_file_name(file_name):

   a = os.path.splitext(file_name)[0]
   a = a.split("/")[:-1]
   a.append(" ")
   where_str = "/".join(a)

   b = os.path.splitext(file_name)[0]
   b = b.split("/")[-1]
   b = b.split("_")

   base_name = b[0]
   snap_n    = b[1]

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

        # set the layout
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addLayout(self.hbox)
        layout.addWidget(self.canvas)
        layout.addWidget(self.slider)
        self.setLayout(layout)

        # actual data stuff
        self.fpath = first_file_name
        # self.param = get_bifrost_param(first_file_name,0)
        # self.b, self.base_name, self.snap_n = get_bifrost_obj(self.fpath,0)

        # self.data = np.einsum('ijk->kji', self.data)

        self.tag = 'r'
        # self.get_data()

    def keyPressEvent(self, event):
        
        key = event.key

        if key == Qt.Qt.Key_T:
            self.toolbar.show()
        elif key == Qt.Qt.Key_H:
            self.toolbar.hide()

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
        self.slider.setMinimum(0)
        self.slider.setMaximum(self.data.shape[2]-1)

        if self.slider.value() >= self.data.shape[2]:
            self.slider.setValue(self.data.shape[2]-1)

        self.setCombo()

    def home(self):
        self.toolbar.home()
    def zoom(self):
        self.toolbar.zoom()
    def pan(self):
        self.toolbar.pan()

    def plot(self):
			plt.clf()
			image = self.data[:,:,self.slider.value()]
			image = np.fliplr(image)
			image = np.rot90(image,k=2)
			
			label = "Value"
			color = cm.get_cmap('jet')
			
			ax = self.figure.add_subplot(111)
			ax.set_title("[%s] %s (Snap: %s) for z = %f \n[time: %s]" % (self.tag, self.base_name, self.snap_n, self.b.z[self.slider.value()],str(datetime.timedelta(seconds=self.param['t']*self.param['u_t']))))
			ax.set_ylabel('y-direction')
			ax.set_xlabel('x-direction')
			
			ax.xaxis.set_major_locator(ticker.MultipleLocator(int(64)))
			ax.yaxis.set_major_locator(ticker.MultipleLocator(int(64)))
			
			extension = [0, self.param['mx'], 0, self.param['my']]
			
			if self.check_si.isChecked():
				ax.set_ylabel('y-direction [Mm]')
				ax.set_xlabel('x-direction [Mm]')
				
				ax.xaxis.set_major_locator(ticker.MultipleLocator(int(4)))
				ax.yaxis.set_major_locator(ticker.MultipleLocator(int(4)))
				
				extension = [0., self.param['dx']*self.param['mx'], 0.0, self.param['dy']*self.param['my']]
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
				color = cm.get_cmap('gist_yarg')
			
			im = ax.imshow(image, interpolation='none', origin='lower', cmap=color, extent=extension)
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

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    main = Window()
    main.setWindowTitle('Bifrost Q(t4)uick Look App')
    main.show()

    sys.exit(app.exec_())
