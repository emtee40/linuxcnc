#!/usr/bin/env python
# qtVcp actions
#
# Copyright (c) 2017  Chris Morley <chrisinnanaimo@hotmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# Action buttons are used to change linuxcnc behaivor do to button pushing.
# By making the button 'checkable' in the designer editor, the buton will toggle.
# In the designer editor, it is possible to select what the button will do.
#################################################################################

from PyQt4 import QtCore, QtGui
from qtvcp_widgets.simple_widgets import _HalWidgetBase
from qtvcp.qt_glib import GStat, Lcnc_Action
from qtvcp.qt_istat import IStat
from qtscreen.aux_program_loader import Aux_program_loader
import linuxcnc

# Instiniate the libraries with global reference
# GSTAT gives us status messages from linuxcnc
# ACTION gives commands to linuxcnc
GSTAT = GStat()
ACTION = Lcnc_Action()
INI = IStat()
AUX_PRGM = Aux_program_loader()

class Lcnc_ActionButton(QtGui.QPushButton, _HalWidgetBase):
    def __init__(self, parent = None):
        QtGui.QPushButton.__init__(self, parent)
        #self.setCheckable(False)
        self._block_signal = False
        self.estop = True
        self.machine_on = False
        self.home = False
        self.run = False
        self.abort = False
        self.pause = False
        self.load_dialog = False
        self.jog_joint_pos = False
        self.jog_joint_neg = False
        self.zero_axis = False
        self.joint_number = 0
        self.launch_halmeter = False
        self.launch_status = False
        self.launch_halshow = False
        self.mdi = False
        self.auto = False
        self.manual = False

    ##################################################
    # This gets called by qtvcp_makepins
    # It infers HAL involvement but there is none
    # GSTAT is used to synch the buttons in case
    # other entities change linuxcnc's state
    # also some buttons are disabled/enabled based on
    # linuxcnc state / possible actions
    #
    # _safecheck blocks the outgoing signal so
    # the buttons can be synced with linuxcnc
    # without setting an infinite loop
    ###################################################
    def _hal_init(self):
        def _safecheck(state,data=None):
            self._block_signal = True
            self.setChecked(state)
            self._block_signal = False

        def test():
            return (GSTAT.machine_is_on() and \
                ( GSTAT.is_all_homed() or INI.NO_HOME_REQUIRED) and \
                    GSTAT.is_file_loaded() )

        if self.estop:
            # Estop starts with button down - in estop which
            # backwards logic for the button...
            if self.isCheckable():_safecheck(True)
            GSTAT.connect('state-estop', lambda w: _safecheck(True))
            GSTAT.connect('state-estop-reset', lambda w: _safecheck(False))

        elif self.machine_on:
            #self.setEnabled(False)
            GSTAT.connect('state-estop', lambda w: self.setEnabled(False))
            GSTAT.connect('state-estop-reset', lambda w: self.setEnabled(True))
            GSTAT.connect('state-on', lambda w: _safecheck(True))
            GSTAT.connect('state-off', lambda w: _safecheck(False))

        elif self.home:
            #self.setEnabled(False)
            GSTAT.connect('state-off', lambda w: self.setEnabled(False))
            GSTAT.connect('state-estop', lambda w: self.setEnabled(False))
            GSTAT.connect('interp-idle', lambda w: self.setEnabled(GSTAT.machine_is_on()))
            GSTAT.connect('interp-run', lambda w: self.setEnabled(False))
            GSTAT.connect('all-homed', lambda w: _safecheck(True))
            GSTAT.connect('not-all-homed', lambda w, axis: _safecheck(False, axis))

        elif self.load_dialog:
            GSTAT.connect('state-off', lambda w: self.setEnabled(False))
            GSTAT.connect('state-estop', lambda w: self.setEnabled(False))
            GSTAT.connect('interp-idle', lambda w: self.setEnabled(GSTAT.machine_is_on()))
            GSTAT.connect('interp-run', lambda w: self.setEnabled(False))
            GSTAT.connect('all-homed', lambda w: _safecheck(True))

        elif self.jog_joint_pos or self.jog_joint_neg:
            GSTAT.connect('state-off', lambda w: self.setEnabled(False))
            GSTAT.connect('state-estop', lambda w: self.setEnabled(False))
            GSTAT.connect('interp-idle', lambda w: self.setEnabled(GSTAT.machine_is_on()))
            GSTAT.connect('interp-run', lambda w: self.setEnabled(False))
            if self.jog_joint_pos:
                self.pressed.connect(lambda : self.jog_action(1))
            else:
                self.pressed.connect(lambda : self.jog_action(-1))
            self.released.connect(lambda : self.jog_action(0))
            # jog button use diferent action signals so
            # leave early to aviod the standard 'clicked' signal
            return

        elif self.zero_axis or self.run:
            GSTAT.connect('state-off', lambda w: self.setEnabled(False))
            GSTAT.connect('state-estop', lambda w: self.setEnabled(False))
            GSTAT.connect('interp-idle', lambda w: self.setEnabled(test()))
            GSTAT.connect('interp-run', lambda w: self.setEnabled(False))
            GSTAT.connect('all-homed', lambda w: self.setEnabled(True))

        elif self.abort or self.abort or self.pause:
            self.setEnabled(False)
            GSTAT.connect('state-off', lambda w: self.setEnabled(False))
            GSTAT.connect('state-estop', lambda w: self.setEnabled(False))
            GSTAT.connect('interp-idle', lambda w: self.setEnabled(test()))
            GSTAT.connect('all-homed', lambda w: self.setEnabled(True))

        elif self.launch_halmeter:
            pass
        elif self.launch_status:
            pass
        elif self.launch_halshow:
            pass
        elif self.auto:
            GSTAT.connect('mode-auto', lambda w: _safecheck(True))
        elif self.mdi:
            GSTAT.connect('mode-mdi', lambda w: _safecheck(True))
        elif self.manual:
            GSTAT.connect('mode-manual', lambda w: _safecheck(True))
        # connect a signal and callback function to the button
        self.clicked[bool].connect(self.action)

    ###################################
    # Here we do the actions
    ###################################
    def action(self,state = None):
        # don't do anything if the signal is blocked
        if self._block_signal: return
        if self.estop:
            if self.isCheckable():
                ACTION.SET_ESTOP_STATE(state)
            else:
                ACTION.SET_ESTOP_STATE(GSTAT.estop_is_clear())
        elif self.machine_on:
           if self.isCheckable():
                ACTION.SET_MACHINE_STATE(state)
           else:
                print 'gstat:',GSTAT.machine_is_on
                ACTION.SET_MACHINE_STATE(not GSTAT.machine_is_on())
        elif self.home:
           if self.isCheckable():
                if state:
                    ACTION.SET_MACHINE_HOMING(self.joint_number)
                else:
                    ACTION.SET_MACHINE_UNHOMED(self.joint_number)
           else:
                if GSTAT.is_all_homed():
                    ACTION.SET_MACHINE_UNHOMED(self.joint_number)
                else:
                    ACTION.SET_MACHINE_HOMING(self.joint_number)
        elif self.run:
            ACTION.RUN()
        elif self.abort:
            ACTION.ABORT()
        elif self.pause:
            ACTION.PAUSE()
        elif self.load_dialog:
            GSTAT.emit('load-file-request')
        elif self.zero_axis:
            j = "XYZABCUVW"
            try:
                axis = j[self.joint_number]
            except:
                print '''can't zero origin for specified jpint;''', self.joint_number
            ACTION.SET_AXIS_ORIGIN(axis, 0)
        elif self.launch_halmeter:
            AUX_PRGM.load_halmeter()
        elif self.launch_status:
            AUX_PRGM.load_status()
        elif self.launch_halshow:
            AUX_PRGM.load_halshow()
        elif self.auto:
            ACTION.SET_AUTO_MODE()
        elif self.mdi:
            ACTION.SET_MDI_MODE()
        elif self.manual:
            ACTION.SET_MANUAL_MODE()
        # defult error case
        else:
            print 'QTVCP: action button: * No action recognised *'

    def jog_action(self,direction):
        if direction == 0 and GSTAT.current_jog_distance != 0: return
        if direction:
            ACTION.ensure_mode(linuxcnc.MODE_MANUAL)
        GSTAT.continuous_jog(self.joint_number, direction, GSTAT.current_jog_distance)

    #########################################################################
    # This is how designer can interact with our widget properties.
    # designer will show the pyqtProperty properties in the editor
    # it will use the get set and reset calls to do those actions
    #
    # _toggle_properties makes it so we can only select one option
    ########################################################################

    def _toggle_properties(self, picked):
        data = ('estop','machine_on','home','run','abort','pause',
                    'load_dialog','jog_joint_pos', 'jog_joint_neg','zero_axis',
                    'launch_halmeter','launch_status', 'launch_halshow',
                    'auto','mdi','manual')

        for i in data:
            if not i == picked:
                self[i+'_action'] = False

    def set_estop(self, data):
        self.estop = data
        if data:
            self._toggle_properties('estop')
    def get_estop(self):
        return self.estop
    def reset_estop(self):
        self.estop = False

    def set_machine_on(self, data):
        self.machine_on = data
        if data:
            self._toggle_properties('machine_on')
    def get_machine_on(self):
        return self.machine_on
    def reset_machine_on(self):
        self.machine_on = False

    def set_home(self, data):
        self.home = data
        if data:
            self._toggle_properties('home')
    def get_home(self):
        return self.home
    def reset_home(self):
        self.home = False

    def set_zero_axis(self, data):
        self.zero_axis = data
        if data:
            self._toggle_properties('zero_axis')
    def get_zero_axis(self):
        return self.zero_axis
    def reset_zero_axis(self):
        self.zero_axis = False

    def set_load_dialog(self, data):
        self.load_dialog = data
        if data:
            self._toggle_properties('load_dialog')
    def get_load_dialog(self):
        return self.load_dialog
    def reset_load_dialog(self):
        self.load_dialog = False

    def set_jog_joint_pos(self, data):
        self.jog_joint_pos = data
        if data:
            self._toggle_properties('jog_joint_pos')
    def get_jog_joint_pos(self):
        return self.jog_joint_pos
    def reset_jog_joint_pos(self):
        self.jog_joint_pos = False

    def set_jog_joint_neg(self, data):
        self.jog_joint_neg = data
        if data:
            self._toggle_properties('jog_joint_neg')
    def get_jog_joint_neg(self):
        return self.jog_joint_neg
    def reset_jog_joint_neg(self):
        self.jog_joint_neg = False

    def set_run(self, data):
        self.run = data
        if data:
            self._toggle_properties('run')
    def get_run(self):
        return self.run
    def reset_run(self):
        self.run = False

    def set_abort(self, data):
        self.abort = data
        if data:
            self._toggle_properties('abort')
    def get_abort(self):
        return self.abort
    def reset_abort(self):
        self.abort = False

    def set_pause(self, data):
        self.pause = data
        if data:
            self._toggle_properties('pause')
    def get_pause(self):
        return self.pause
    def reset_pause(self):
        self.pause = False

    def set_launch_halmeter(self, data):
        self.launch_halmeter = data
        if data:
            self._toggle_properties('launch_halmeter')
    def get_launch_halmeter(self):
        return self.launch_halmeter
    def reset_launch_halmeter(self):
        self.launch_halmeter = False

    def set_launch_status(self, data):
        self.launch_status = data
        if data:
            self._toggle_properties('launch_status')
    def get_launch_status(self):
        return self.launch_status
    def reset_launch_status(self):
        self.launch_status = False

    def set_launch_halshow(self, data):
        self.launch_halshow = data
        if data:
            self._toggle_properties('launch_halshow')
    def get_launch_halshow(self):
        return self.launch_halshow
    def reset_launch_halshow(self):
        self.launch_halshow = False

    def set_auto(self, data):
        self.auto = data
        if data:
            self._toggle_properties('auto')
    def get_auto(self):
        return self.auto
    def reset_auto(self):
        self.auto = False

    def set_mdi(self, data):
        self.mdi = data
        if data:
            self._toggle_properties('mdi')
    def get_mdi(self):
        return self.mdi
    def reset_mdi(self):
        self.mdi = False

    def set_manual(self, data):
        self.manual = data
        if data:
            self._toggle_properties('manual')
    def get_manual(self):
        return self.manual
    def reset_manual(self):
        self.manual = False

    def set_joint(self, data):
        self.joint = data
    def get_joint(self):
        return self.joint
    def reset_joint(self):
        self.joint = -1

    # designer will show these properties in this order:
    estop_action = QtCore.pyqtProperty(bool, get_estop, set_estop, reset_estop)
    machine_on_action = QtCore.pyqtProperty(bool, get_machine_on, set_machine_on, reset_machine_on)
    auto_action = QtCore.pyqtProperty(bool, get_auto, set_auto, reset_auto)
    mdi_action = QtCore.pyqtProperty(bool, get_mdi, set_mdi, reset_mdi)
    manual_action = QtCore.pyqtProperty(bool, get_manual, set_manual, reset_manual)
    run_action = QtCore.pyqtProperty(bool, get_run, set_run, reset_run)
    abort_action = QtCore.pyqtProperty(bool, get_abort, set_abort, reset_abort)
    pause_action = QtCore.pyqtProperty(bool, get_pause, set_pause, reset_pause)
    load_dialog_action = QtCore.pyqtProperty(bool, get_load_dialog, set_load_dialog, reset_load_dialog)
    launch_halmeter_action = QtCore.pyqtProperty(bool, get_launch_halmeter, set_launch_halmeter, reset_launch_halmeter)
    launch_status_action = QtCore.pyqtProperty(bool, get_launch_status, set_launch_status, reset_launch_status)
    launch_halshow_action = QtCore.pyqtProperty(bool, get_launch_halshow, set_launch_halshow, reset_launch_halshow)
    home_action = QtCore.pyqtProperty(bool, get_home, set_home, reset_home)
    zero_axis_action = QtCore.pyqtProperty(bool, get_zero_axis, set_zero_axis, reset_zero_axis)
    jog_joint_pos_action = QtCore.pyqtProperty(bool, get_jog_joint_pos, set_jog_joint_pos, reset_jog_joint_pos)
    jog_joint_neg_action = QtCore.pyqtProperty(bool, get_jog_joint_neg, set_jog_joint_neg, reset_jog_joint_neg)
    joint_number = QtCore.pyqtProperty(int, get_joint, set_joint, reset_joint)

    ##############################
    # required class boiler code #
    ##############################

    def __getitem__(self, item):
        return getattr(self, item)
    def __setitem__(self, item, value):
        return setattr(self, item, value)

if __name__ == "__main__":

    import sys
    from PyQt4.QtGui import QApplication
    app = QApplication(sys.argv)

    widget = Lcnc_ActionButton('Action')
    # this doesn't get called without qtvcp loading the widget
    widget._hal_init()

    widget.show()
    sys.exit(app.exec_())
