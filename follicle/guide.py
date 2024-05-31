# MGEAR is under the terms of the MIT License

# Copyright (c) 2016 Jeremie Passerin, Miquel Campos
"""Guide Foot banking 01 module"""

from functools import partial
import pymel.core as pm

from mgear.shifter.component import guide
from mgear.core import transform, pyqt
from mgear.vendor.Qt import QtWidgets, QtCore

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya.app.general.mayaMixin import MayaQDockWidget

from . import settingsUI as sui

import maya.cmds as cmds

# guide info
AUTHOR = "Kaiwen Yu"
URL = ""
EMAIL = "kaiwen.yu2018@gmail.com"
VERSION = [1, 0, 0]
TYPE = "follicle"
NAME = "follicle"
DESCRIPTION = ""

##########################################################
# CLASS
##########################################################


class Guide(guide.ComponentGuide):
    """Component Guide Class"""

    compType = TYPE
    compName = NAME
    description = DESCRIPTION

    author = AUTHOR
    url = URL
    email = EMAIL
    version = VERSION

    def postInit(self):
        """Initialize the position for the guide"""
        self.save_transform = ["root", "#_loc"]
        self.addMinMax("#_loc", 1, -1)

    def addObjects(self):
        """Add the Guide Root, blade and locators"""

        self.root = self.addRoot()

        self.locs = self.addLocMulti("#_loc", self.root)

        for loc in self.locs[1:]:
            cmds.parent(loc.name(), self.root.name())

        centers = [self.root]
        centers.extend(self.locs)


    def addParameters(self):
        """Add the configurations settings"""

        self.surface_type = self.addParam("surfaceName", "string", "noInput")

        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam(
            "parentJointIndex", "long", -1, None, None)


##########################################################
# Setting Page
##########################################################

class settingsTab(QtWidgets.QDialog, sui.Ui_Form):
    """The Component settings UI"""

    def __init__(self, parent=None):
        super(settingsTab, self).__init__(parent)
        self.setupUi(self)
        

class componentSettings(MayaQWidgetDockableMixin, guide.componentMainSettings):
    """Create the component setting window"""

    def __init__(self, parent=None):
        self.toolName = TYPE
        # Delete old instances of the componet settings window.
        pyqt.deleteInstances(self, MayaQDockWidget)

        super(self.__class__, self).__init__(parent=parent)
        self.settingsTab = settingsTab()

        self.setup_componentSettingWindow()
        self.create_componentControls()
        self.populate_componentControls()
        self.create_componentLayout()
        self.create_componentConnections()

    def setup_componentSettingWindow(self):
        self.mayaMainWindow = pyqt.maya_main_window()

        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle(TYPE)
        self.resize(280, 350)

    def create_componentControls(self):
        return

    def populate_componentControls(self):
        """Populate Controls

        Populate the controls values from the custom attributes of the
        component.

        """
        # populate tab
        self.tabs.insertTab(1, self.settingsTab, "Component Settings")

        # populate component settings
        # self.populateCheck(self.settingsTab.useRollCtl_checkBox, "useRollCtl")
        # self.settingsTab.rollAngle_spinBox.setValue(
        #     self.root.attr("rollAngle").get())

        # populate connections in main settings
        for cnx in Guide.connectors:
            self.mainSettingsTab.connector_comboBox.addItem(cnx)

        cBox = self.mainSettingsTab.connector_comboBox
        self.connector_items = [cBox.itemText(i) for i in range(cBox.count())]
        currentConnector = self.root.attr("connector").get()
        if currentConnector not in self.connector_items:
            self.mainSettingsTab.connector_comboBox.addItem(currentConnector)
            self.connector_items.append(currentConnector)
            pm.displayWarning("The current connector: %s, is not a valid "
                              "connector for this component. "
                              "Build will Fail!!")
        comboIndex = self.connector_items.index(currentConnector)
        self.mainSettingsTab.connector_comboBox.setCurrentIndex(comboIndex)

        self.settingsTab.surfaceLineEdit.setText(self.root.attr("surfaceName").get())

    def create_componentLayout(self):

        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):

        def update_surface_name(surface_name):
            validation_passed = True
            # try:
            #     if cmds.objectType(surface_name) != "mesh" and cmds.objectType(surface_name) != "nurbsSurface":
            #         validation_passed = False
            # except RuntimeError:
            #     validation_passed = False
            #try asking first born son https://discourse.techart.online/t/amaya-python-selecting-the-transform-of-a-shape/2690

            if validation_passed:
                self.root.attr("surfaceName").set(surface_name)
                self.settingsTab.surfaceLineEdit.setText(self.root.attr("surfaceName").get())
            else:
                pm.displayWarning("Invalid selection for surface")
                self.settingsTab.surfaceLineEdit.clear()

        def update_from_button():
            selected = cmds.ls(selection=True)
            if len(selected) != 1:
                pm.displayWarning("Invalid selection for surface")
                return
            update_surface_name(surface_name=selected[0])

        self.settingsTab.surfaceLineEdit.editingFinished.connect(
            lambda: update_surface_name(self.settingsTab.surfaceLineEdit.text()))
        self.settingsTab.surfaceLoadButton.clicked.connect(update_from_button)


    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
