"""Component Foot Banking 02 module"""
import ast

import pymel.core as pm
from pymel.core import datatypes
import maya.cmds as cmds
import maya.OpenMaya as om

import mgear

from mgear.shifter import component

from mgear.core import node, applyop, vector
from mgear.core import attribute, transform, primitive


class Component(component.Main):
    """Shifter component Class"""

    # =====================================================
    # OBJECTS
    # =====================================================
    def addObjects(self):
        """Add all the objects needed to create the component."""

        surface_name = self.settings["surfaceName"]

        # create pseudo locators at the MGear guide multi locators
        pseudo_locator_lst = []
        pseudo_locator_group = cmds.group(empty=True, name="pseudo_locator_grp")
        for i, pos_key in enumerate(self.guide.pos):
            if pos_key == "root":
                continue
            pos_vector = self.guide.pos[pos_key]
            pseudo_locator = cmds.spaceLocator(name="pseudoLocator_" + str(i))[0]
            cmds.setAttr(pseudo_locator + ".translateX", pos_vector.x)
            cmds.setAttr(pseudo_locator + ".translateY", pos_vector.y)
            cmds.setAttr(pseudo_locator + ".translateZ", pos_vector.z)
            pseudo_locator_lst.append(pseudo_locator)
            cmds.parent(pseudo_locator, pseudo_locator_group)

        # put the pseudo locators under rig|setup
        cmds.parent(pseudo_locator_group, "rig|setup")

        # create follicles
        # note that this is a dict of follicle transform name mapped to follicle shape name
        follicles_trans_lst = self.create_follicles(surface_name, pseudo_locator_lst)

        ctl_lst = []
        for i, follicle_trans in enumerate(follicles_trans_lst):
            curr_transform_matrix = cmds.xform(follicle_trans, query=True, matrix=True)
            ctl_name = follicle_trans + "_ctl"
            os_grp_name = "follicle_" + str(i) + "_os_grp"
            os_grp = primitive.addTransform(self.root, os_grp_name, curr_transform_matrix)
            ik_cns = primitive.addTransform(os_grp, "follicle_" + str(i) + "_ik_cns", curr_transform_matrix)

            print("Parent control tag: ")
            print(self.parentCtlTag)

            ctl = self.addCtl(ik_cns,
                              ctl_name,
                              curr_transform_matrix,
                              self.color_ik,
                              "cube",
                              w=self.size * 0.2,
                              h=self.size * 0.2,
                              d=self.size * 0.2,
                              tp=self.parentCtlTag,
                              guide_loc_ref="root")
            ctl_lst.append(ctl)
            cmds.parentConstraint(follicle_trans, os_grp.name(), mo=True)

        # add joints by populating mgear component's dictionary
        for ctl_name in ctl_lst:
            self.jnt_pos.append(
                {
                    "obj": ctl_name,
                    "name": ctl_name,
                    "newActiveJnt": "component_jnt_org",
                    "guide_relative": "root",
                    "UniScale": True,
                    "leaf_joint": False,
                }
            )

    def create_follicles(self, surface_name, locator_list):
        """
        Create follicles based on the locator_list. Currently surface_name does nothing.

        Returns a list of the follicle's transform names as String
        """

        fol_grp = cmds.group(empty=True, name="follicle_grp")
        cmds.parent(fol_grp, "rig|setup")

        surface_shape = cmds.listRelatives(surface_name, type="shape")[0]
        shape_type = cmds.nodeType(surface_shape)
        follicle_trans_list = []
        closest_point_node_list = []

        # TODO: figure out the surface type properly, by using checking children
        surface_type = cmds.nodeType(surface_name)

        for n, loc in enumerate(locator_list):
            # Create Point on Curve Info node
            if shape_type == "nurbsSurface":
                closest_point_node = cmds.createNode("closestPointOnSurface", n="cps")
                closest_point_node_list.append(closest_point_node)
            elif shape_type == "mesh":
                closest_point_node = cmds.createNode("closestPointOnMesh", n="cpm")
                closest_point_node_list.append(closest_point_node)
            else:
                cmds.warning("Please select a NURBS surface nor a mesh")
                return

            # Print locator position
            loc_position = cmds.xform(loc, query=True, translation=True, worldSpace=True)
            print("Locator Position {}: {}".format(n, loc_position))

            # Connect surface to closestPointOnSurface node
            if shape_type == "nurbsSurface":
                cmds.connectAttr(surface_shape + ".local", closest_point_node + ".inputSurface", force=True)
                cmds.connectAttr("{}.local".format(surface_shape), "{}.inputSurface".format(closest_point_node),
                                 force=True)
            else:
                cmds.connectAttr("{}.worldMatrix".format(surface_shape), "{}.inputMatrix".format(closest_point_node), force=True)
                cmds.connectAttr("{}.outMesh".format(surface_shape), "{}.inMesh".format(closest_point_node), force=True)



            # Connect locator to closestPointOnSurface node
            cmds.connectAttr(loc + ".translate", closest_point_node + ".inPosition")

            # Get UV parameters from closestPointOnSurface node
            parameter_u = cmds.getAttr(closest_point_node + ".parameterU")
            parameter_v = cmds.getAttr(closest_point_node + ".parameterV")
            print("Closest Point UV Parameters {}: (U={}, V={})".format(n, parameter_u, parameter_v))

            # Create follicle on surface
            follicle_data = self.create_one_follicle(input_surface=[surface_shape], parent_grp=fol_grp, hide=0,
                                                     name="{}_{}".format(self.settings["comp_name"], n))
            follicle_trans_list.append(follicle_data['transform'])

            # Print UV parameters used for follicle creation
            print("Follicle UV Parameters {}: (U={}, V={})".format(n, parameter_u, parameter_v))

            # Connect closestPointOnSurface to follicle
            cmds.connectAttr("{}.parameterV".format(closest_point_node),
                             "{}.parameterV".format(follicle_data['shape']), force=True)
            cmds.connectAttr("{}.parameterU".format(closest_point_node),
                             "{}.parameterU".format(follicle_data['shape']), force=True)

            # Disconnect closestPointOnSurface from follicle
            cmds.disconnectAttr("{}.parameterV".format(closest_point_node),
                                "{}.parameterV".format(follicle_data['shape']))
            cmds.disconnectAttr("{}.parameterU".format(closest_point_node),
                                "{}.parameterU".format(follicle_data['shape']))

            # Remove closestPointOnSurface node
            cmds.delete(closest_point_node)

        return follicle_trans_list

    def create_one_follicle(self, input_surface, parent_grp, scale_grp='', u_val=0.5, v_val=0.5, hide=1, name='follicle'):
        """
        Creates one follicle on nurbs surface or geo
        :param input_surface: shape node
        :param parent_grp: name of the parent group for the follicle
        :param u_val:
        :param v_val:
        :param hide:
        :param name:
        :return follicle_data:
            dict {'transform': follicle transform,
                'shape': follicle shape}
        """
        # Create a follicle
        follicle_shape = cmds.createNode('follicle')
        # Get the transform of the follicle
        follicle = cmds.listRelatives(follicle_shape, parent=True)[0]
        # Rename the follicle
        follicle = cmds.rename(follicle, name)
        follicle_shape = cmds.rename(cmds.listRelatives(follicle, c=True)[0], (name + 'Shape'))

        # If the inputSurface is of type 'nurbsSurface', connect the surface to the follicle
        if cmds.objectType(input_surface[0]) == 'nurbsSurface':
            cmds.connectAttr((input_surface[0] + '.local'), (follicle_shape + '.inputSurface'))
        # If the inputSurface is of type 'mesh', connect the surface to the follicle
        if cmds.objectType(input_surface[0]) == 'mesh':
            cmds.connectAttr((input_surface[0] + '.outMesh'), (follicle_shape + '.inputMesh'))

        # Connect the worldMatrix of the surface into the follicleShape
        cmds.connectAttr((input_surface[0] + '.worldMatrix[0]'), (follicle_shape + '.inputWorldMatrix'))
        # Connect the follicleShape to it's transform
        cmds.connectAttr((follicle_shape + '.outRotate'), (follicle + '.rotate'))
        cmds.connectAttr((follicle_shape + '.outTranslate'), (follicle + '.translate'))
        # Set the uValue and vValue for the current follicle
        cmds.setAttr((follicle_shape + '.parameterU'), u_val)
        cmds.setAttr((follicle_shape + '.parameterV'), v_val)
        # Lock the translate/rotate of the follicle
        cmds.setAttr((follicle + '.translate'), lock=True)
        cmds.setAttr((follicle + '.rotate'), lock=True)

        # If it was set to be hidden, hide the follicle
        if hide:
            cmds.setAttr((follicle_shape + '.visibility'), 0)
        # If a scale-group was defined and exists
        if scale_grp and cmds.objExists(scale_grp):
            # Connect the scale-group to the follicle
            cmds.connectAttr((scale_grp + '.scale'), (follicle + '.scale'))
            # Lock the scale of the follicle
            cmds.setAttr((follicle + '.scale'), lock=True)

        cmds.parent(follicle, parent_grp)

        return {'transform': follicle,
                'shape': follicle_shape}


    # =====================================================
    # CONNECTOR
    # =====================================================
    def setRelation(self):
        """Set the relation beetween object from guide to rig"""
        pass

    def addConnection(self):
        """Add more connection definition to the set"""
        pass

