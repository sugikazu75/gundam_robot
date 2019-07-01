#!/usr/bin/env python

# Copyright (c) 2016, 2017, 2018 Kei Okada
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the Kei Okada nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from collada import *
from urdf_parser_py.urdf import *
from tf.transformations import *
import copy
import os
import sys
import math
import numpy
import argparse
# xmlutil.COLLADA_NS = 'http://www.collada.org/2008/03/COLLADASchema'

depth_ = 0
scale_ = 0.1  # original file uses cm unit
all_weight_ = 0.0
zero_pid = {'p': 0.0, 'i': 0.0, 'd': 0.0}
default_pid = {'p': 10000000.0, 'i': 500.0, 'd': 200000.0}
head_pid = {'p': 1000000.0, 'i': 500.0, 'd': 200000.0}
torso_pid = {'p': 20000000.0, 'i': 10000.0, 'd': 2000000.0}
elbow_p_mimic_pid = {'p': 1000000.0, 'i': 500.0, 'd': 200000.0}
wrist_pid = {'p': 100000.0, 'i': 50.0, 'd': 20000.0}
gripper_pid = {'p': 100000.0, 'i': 100.0, 'd': 500.0}
finger_pid = {'p': 100000.000000, 'i': 100.000000, 'd': 500.000000}
crotch_p_pid = {'p': 400000000.0, 'i': 4000000.0, 'd': 2000000.0}
crotch_r_pid = {'p': 200000000.0, 'i': 1000000.0, 'd': 1000000.0}
crotch_y_pid = {'p': 200000000.0, 'i': 1000000.0, 'd': 1000000.0}
knee_p_pid = {'p': 100000000.0, 'i': 100000.0, 'd': 1000000.0}
knee_p_mimic_pid = {'p': 10000000.0, 'i': 100000.0, 'd': 1000000.0}
ankle_pid = {'p': 100000000.0, 'i': 5000.0, 'd': 1000000.0}
ankle_p_mimic_pid = {'p': 500000.0, 'i': 500.0, 'd': 50000.0}
cover_pid = {'p': 50000.0, 'i': 500.0, 'd': 5000.0}
joints_ = {
    # axis [pitch, roll, yaw]
    # backpack
    'rx78_Null_013': {'joint_type': 'fixed'},
      'rx78_Null_012': {'joint_type': 'fixed'},  # sword
        'rx78_Null_011': {'joint_type': 'fixed'},
        'rx78_Null_010': {'joint_type': 'fixed'},
      'rx78_Null_009': {'joint_type': 'fixed'},
        'rx78_Null_008': {'joint_type': 'fixed'},
        'rx78_Null_007': {'joint_type': 'fixed'},
      'rx78_Null_005': {'joint_type': 'fixed'},  # jet
      'rx78_Null_006': {'joint_type': 'fixed'},
    'rx78_Null_082': {'joint_type': 'fixed'},  # skip torso parts, which is also has another joint
    'rx78_Null_083': {'joint_type': 'fixed'},  # torso?

    # torso
    'rx78_Null_018': {'name': 'torso_waist_y', 'axis': [0, 0, 1], 'limit_lower': -math.pi / 12, 'limit_upper': math.pi / 12, 'pid': torso_pid},
    'rx78_Null_017': {'name': 'torso_waist_p', 'axis': [1, 0, 0], 'limit_lower': -math.pi / 4, 'limit_upper': math.pi / 4, 'pid': torso_pid},
    'rx78_Null_016': {'mimic': 'rx78_Null_017', 'axis': [1, 0, 0]},

    # head
    'rx78_Null_015': {'name': 'head_neck_y', 'axis': [0, 0, 1], 'pid': head_pid},
    'rx78_Null_014': {'name': 'head_neck_p', 'axis': [1, 0, 0], 'limit_lower': -math.pi / 5, 'pid': head_pid},

    # larm
    'rx78_Null_004': {'name': 'larm_shoulder_p', 'axis': [1, 0, 0]},
    'rx78_Null_001': {'name': 'larm_shoulder_r', 'axis': [0, -1, 0], 'limit_lower': -math.pi / 6},
    'rx78_Null_002': {'name': 'larm_shoulder_y', 'axis': [0, 0, 1]},
    'rx78_Null_003': {'name': 'larm_elbow_p', 'axis': [1, 0, 0], 'limit_lower': -math.pi / 3, 'limit_upper': math.pi / 24},
    'rx78_Null_066': {'mimic': 'rx78_Null_003', 'axis': [1, 0, 0], 'pid': elbow_p_mimic_pid},
    'rx78_Null_067': {'name': 'larm_wrist_y', 'axis': [0, 0, 1], 'pid': wrist_pid},
    'rx78_Null_069': {'name': 'larm_wrist_r', 'axis': [0, -1, 0], 'pid': wrist_pid},
    'rx78_Null_048': {'joint_type': 'fixed'},  # shoulder-p cover
    'rx78_Null_065': {'joint_type': 'fixed'},  # elbow-p internal
    # left hand
    'rx78_Null_059': {'mimic': 'rx78_Null_062', 'axis': [0, 1, 0], 'pid': finger_pid},  # index
      'rx78_Null_060': {'mimic': 'rx78_Null_062', 'axis': [0, 1, 0], 'pid': finger_pid},
      'rx78_Null_061': {'mimic': 'rx78_Null_062', 'axis': [0, 1, 0], 'pid': finger_pid},
    'rx78_Null_062': {'name': 'larm_gripper', 'axis': [0, 1, 0], 'limit_lower': -math.pi / 24, 'pid': gripper_pid},  # thumb
      'rx78_Null_063': {'mimic': 'rx78_Null_062', 'mimic_offset': -math.pi / 4, 'axis': [1, 0, 0], 'pid': finger_pid},
      'rx78_Null_064': {'mimic': 'rx78_Null_062', 'axis': [1, 0, 0], 'pid': finger_pid},
    'rx78_Null_068': {'mimic': 'rx78_Null_062', 'axis': [0, 1, 0], 'pid': finger_pid},
      'rx78_Null_070': {'mimic': 'rx78_Null_062', 'axis': [0, 1, 0], 'pid': finger_pid},
      'rx78_Null_071': {'mimic': 'rx78_Null_062', 'axis': [0, 1, 0], 'pid': finger_pid},
    'rx78_Null_072': {'mimic': 'rx78_Null_062', 'axis': [0, 1, 0], 'pid': finger_pid},
      'rx78_Null_073': {'mimic': 'rx78_Null_062', 'axis': [0, 1, 0], 'pid': finger_pid},
      'rx78_Null_074': {'mimic': 'rx78_Null_062', 'axis': [0, 1, 0], 'pid': finger_pid},
    'rx78_Null_075': {'mimic': 'rx78_Null_062', 'axis': [0, 1, 0], 'pid': finger_pid},
      'rx78_Null_076': {'mimic': 'rx78_Null_062', 'axis': [0, 1, 0], 'pid': finger_pid},
      'rx78_Null_077': {'mimic': 'rx78_Null_062', 'axis': [0, 1, 0], 'pid': finger_pid},

    # rarm
    'rx78_Null_049': {'name': 'rarm_shoulder_p', 'axis': [1, 0, 0]},
    'rx78_Null_050': {'name': 'rarm_shoulder_r', 'axis': [0, -1, 0], 'limit_upper': math.pi / 6},
    'rx78_Null_051': {'name': 'rarm_shoulder_y', 'axis': [0, 0, 1]},
    'rx78_Null_052': {'name': 'rarm_elbow_p', 'axis': [1, 0, 0], 'limit_lower': -math.pi / 3, 'limit_upper': math.pi / 24},
    'rx78_Null_053': {'mimic': 'rx78_Null_052', 'axis': [1, 0, 0], 'pid': elbow_p_mimic_pid},
    'rx78_Null_054': {'name': 'rarm_wrist_y', 'axis': [0, 0, 1], 'pid': wrist_pid},
    'rx78_Null_055': {'name': 'rarm_wrist_r', 'axis': [0, -1, 0], 'pid': wrist_pid},
    'rx78_Null_081': {'joint_type': 'fixed'},  # shoulder-p cover
    # right hand
    'rx78_Null_021': {'mimic': 'rx78_Null_056', 'axis': [0, -1, 0], 'pid': finger_pid},  # middle
      'rx78_Null_022': {'mimic': 'rx78_Null_056', 'axis': [0, -1, 0], 'pid': finger_pid},
      'rx78_Null_023': {'mimic': 'rx78_Null_056', 'axis': [0, -1, 0], 'pid': finger_pid},
    'rx78_Null_024': {'mimic': 'rx78_Null_056', 'axis': [0, -1, 0], 'pid': finger_pid},  # index
      'rx78_Null_025': {'mimic': 'rx78_Null_056', 'axis': [0, -1, 0], 'pid': finger_pid},
      'rx78_Null_026': {'mimic': 'rx78_Null_056', 'axis': [0, -1, 0], 'pid': finger_pid},
    'rx78_Null_027': {'mimic': 'rx78_Null_056', 'axis': [0, -1, 0], 'pid': finger_pid},  # litle
      'rx78_Null_028': {'mimic': 'rx78_Null_056', 'axis': [0, -1, 0], 'pid': finger_pid},
      'rx78_Null_029': {'mimic': 'rx78_Null_056', 'axis': [0, -1, 0], 'pid': finger_pid},
    'rx78_Null_056': {'name': 'rarm_gripper', 'axis': [0, -1, 0], 'limit_lower': -math.pi / 24, 'pid': gripper_pid},  # thumb
      'rx78_Null_057': {'mimic': 'rx78_Null_056', 'mimic_offset': -math.pi / 4, 'axis': [1, 0, 0], 'pid': finger_pid},
      'rx78_Null_058': {'mimic': 'rx78_Null_056', 'axis': [1, 0, 0], 'pid': finger_pid},
    'rx78_Null_078': {'mimic': 'rx78_Null_056', 'axis': [0, -1, 0], 'pid': finger_pid},  # ring
      'rx78_Null_079': {'mimic': 'rx78_Null_056', 'axis': [0, -1, 0], 'pid': finger_pid},
      'rx78_Null_080': {'mimic': 'rx78_Null_056', 'axis': [0, -1, 0], 'pid': finger_pid},

    # lleg
    'rx78_Null_033': {'mimic': 'rx78_Null_035', 'mimic_multiplier': 0.5, 'pid': cover_pid},  # back cover
    'rx78_Null_034': {'mimic': 'rx78_Null_035', 'mimic_multiplier': 0.5, 'pid': cover_pid},  # front cover
    'rx78_Null_047': {'mimic': 'rx78_object_029', 'mimic_multiplier': -0.6, 'axis': [0, 1, 0], 'pid': cover_pid},  # side cover
    'rx78_Null_035': {'name': 'lleg_crotch_p', 'axis': [1, 0, 0], 'limit_lower': -math.pi / 4, 'limit_upper': math.pi / 4, 'pid': crotch_p_pid},
    'rx78_object_029': {'name': 'lleg_crotch_r', 'joint_type': 'revolute', 'axis': [0, -1, 0], 'limit_lower': -math.pi / 12, 'limit_upper': math.pi / 4, 'pid': crotch_r_pid},  # hack for crotch-r _035->_029->_036
    'rx78_Null_036': {'name': 'lleg_crotch_y', 'axis': [0, 0, 1], 'parent': 'rx78_object_029', 'pid': crotch_y_pid},
    'rx78_Null_037': {'name': 'lleg_knee_p', 'axis': [1, 0, 0], 'limit_lower': -math.pi / 24, 'limit_upper': math.pi / 3, 'pid': knee_p_pid},
    'rx78_Null_038': {'mimic': 'rx78_Null_037', 'axis': [1, 0, 0], 'pid': knee_p_mimic_pid},
    'rx78_Null_039': {'name': 'lleg_ankle_p', 'axis': [1, 0, 0], 'limit_lower': -math.pi / 4, 'limit_upper': math.pi / 4, 'pid': ankle_pid},
    'rx78_Null_041': {'name': 'lleg_ankle_r', 'axis': [-1, 0, 0], 'limit_lower': -math.pi / 12, 'limit_upper': math.pi / 12, 'pid': ankle_pid},

    'rx78_Null_040': {'joint_type': 'fixed', 'parent': 'rx78_Null_041', 'origin_xyz': [1.44559, 0, 0], 'origin_rpy': [0, 0, 0]},  # {'mimic': 'rx78_Null_041',  'axis': [-1, 0, 0]},  # ankle back
    'rx78_Null_042': {'joint_type': 'fixed'},  # sole
    'rx78_Null_043': {'joint_type': 'fixed'},  # sole
    'rx78_Null_044': {'joint_type': 'fixed'},  # sole
    'rx78_Null_045': {'joint_type': 'fixed'},  # sole
    'rx78_Null_046': {'mimic': 'rx78_Null_039', 'mimic_multiplier': -0.5, 'axis': [1, 0, 0], 'pid': ankle_p_mimic_pid},  # ankle cover

    # rleg
    'rx78_Null_084': {'mimic': 'rx78_Null_085', 'mimic_multiplier': 0.5, 'pid': cover_pid},  # front cover
    'rx78_Null_031': {'mimic': 'rx78_Null_085', 'mimic_multiplier': 0.5, 'pid': cover_pid},  # back cover
    'rx78_Null_032': {'mimic': 'rx78_object_086', 'mimic_multiplier': -0.6, 'axis': [0, 1, 0], 'pid': cover_pid},  # side cover
    'rx78_Null_085': {'name': 'rleg_crotch_p', 'axis': [1, 0, 0], 'limit_lower': -math.pi / 4, 'limit_upper': math.pi / 4, 'pid': crotch_p_pid},
    'rx78_object_086': {'name': 'rleg_crotch_r', 'joint_type': 'revolute', 'axis': [0, -1, 0], 'limit_lower': -math.pi / 4, 'limit_upper': math.pi / 12, 'pid': crotch_r_pid},  # hack for crotch-r _085->_086->_086
    'rx78_Null_086': {'name': 'rleg_crotch_y', 'axis': [0, 0, 1], 'parent': 'rx78_object_086', 'pid': crotch_y_pid},
    'rx78_Null_087': {'name': 'rleg_knee_p', 'axis': [1, 0, 0], 'limit_lower': -math.pi / 24, 'limit_upper': math.pi / 3, 'pid': knee_p_pid},
    'rx78_Null_088': {'mimic': 'rx78_Null_087', 'axis': [1, 0, 0], 'pid': knee_p_mimic_pid},
    'rx78_Null_089': {'name': 'rleg_ankle_p', 'axis': [1, 0, 0], 'limit_lower': -math.pi / 4, 'limit_upper': math.pi / 4, 'pid': ankle_pid},
    'rx78_Null_091': {'name': 'rleg_ankle_r', 'axis': [-1, 0, 0], 'limit_lower': -math.pi / 12, 'limit_upper': math.pi / 12, 'pid': ankle_pid},

    'rx78_Null_090': {'joint_type': 'fixed', 'parent': 'rx78_Null_091', 'origin_xyz': [1.44559, 0, 0], 'origin_rpy': [0, 0, 0]},  # {'mimic': 'rx78_Null_091',  'axis': [-1, 0, 0]},  # ankle back
    'rx78_Null_092': {'joint_type': 'fixed'},  # sole
    'rx78_Null_093': {'joint_type': 'fixed'},  # sole
    'rx78_Null_094': {'joint_type': 'fixed'},  # sole
    'rx78_Null_095': {'joint_type': 'fixed'},  # sole
    'rx78_Null_030': {'mimic': 'rx78_Null_089', 'mimic_multiplier': -0.5, 'axis': [1, 0, 0], 'pid': ankle_p_mimic_pid},  # ankle cover

}


def get_bouding_box(geometries):
    bbox_min = []
    bbox_max = []
    for g in geometries:
        for p in g.primitives:
            if p.vertex is not None:
                for i in p.vertex_index:
                    bbox_min.append(scale_ * numpy.amin(p.vertex[i], axis=0))
                    bbox_max.append(scale_ * numpy.amax(p.vertex[i], axis=0))

    xyz = list((numpy.amax(numpy.array(bbox_max), axis=0) +
                numpy.amin(numpy.array(bbox_min), axis=0)) / 2)
    size = list(numpy.amax(numpy.array(bbox_max), axis=0) -
                numpy.amin(numpy.array(bbox_min), axis=0))
    return Collision(
        origin=Pose(xyz=xyz),
        geometry=Box(size=size))


def calc_inertia(collision, density=100.0):
    global all_weight_
    bbox_x = collision.geometry.size[0]
    bbox_y = collision.geometry.size[1]
    bbox_z = collision.geometry.size[2]
    mass = density * bbox_x * bbox_y * bbox_z
    # GGC hack, small mass reduce stability of simulation
    if 1 < mass and mass < 50:
        mass = 50
    all_weight_ += mass
    return Inertial(mass=mass,
                    origin=copy.deepcopy(collision.origin),
                    inertia=Inertia(
                        ixx=mass * (bbox_y * bbox_y + bbox_z * bbox_z) / 12.0,
                        iyy=mass * (bbox_z * bbox_z + bbox_x * bbox_x) / 12.0,
                        izz=mass * (bbox_x * bbox_x + bbox_y * bbox_y) / 12.0))


def retrive_node(nodes, parent=None):
    global robot_, depth_
    # if len(robot_.joints) > 8: return True ############################# FOR
    # DEBUG
    depth_ += 1
    for node in nodes:
        print(' ' * depth_),  # write indent
        try:
            print('id .. {} {}'.format(node.id, type(node)))
        except:
            print('node .. {}'.format(node))
        if isinstance(node, scene.Node):
            if node.id:
                l = Link(name=node.id + '_link',
                         visual=None,
                         inertial=None,
                         collision=None,
                         origin=None)
                if not parent:
                    j = Joint(name=node.id + '_joint',
                              parent='base_link',
                              child=l.name,
                              joint_type='fixed',
                              origin=Pose(rpy=[0, 0, math.pi / 2]))  # Hack for GCC
                else:
                    j = Joint(name=node.id + '_joint',
                              parent=parent.id + '_link',
                              child=l.name,
                              joint_type='fixed',
                              origin=Pose(
                                  xyz=scale_ * translation_from_matrix(node.matrix),
                                  rpy=euler_from_matrix(node.matrix))
                              )
                    print(
                        '{}  - {}'.format(' ' * depth_, [type(n) for n in node.children]))
                    if not any(isinstance(n, scene.GeometryNode) for n in node.children):
                        j.joint_type = 'revolute'
                        # j.axis = numpy.array(parent.matrix)[:3, :3].dot([0,
                        # 0, 1])
                        j.axis = [0, 0, 1]
                        if len(node.transforms) > 1:
                            print(node.transforms[1:])
                        if any(isinstance(n, scene.RotateTransform) for n in node.transforms):
                            j.axis = [1, 0, 0]
                        j.limit = JointLimit(
                            lower=-math.pi / 2, upper=math.pi / 2, effort=1000000000, velocity=1000000)
                    #
                    if node.id in joints_:
                        if 'joint_type' in joints_[node.id]:
                            j.joint_type = joints_[node.id]['joint_type']
                            if j.joint_type == 'fixed':
                                j.limit = None
                                j.axis = None
                            else:
                                j.limit = JointLimit(
                                    lower=-math.pi / 2, upper=math.pi / 2, effort=1000000000, velocity=1000000)
                                j.dynamics = JointDynamics(
                                    damping='0.1', friction='0.0')
                        if 'axis' in joints_[node.id]:
                            j.axis = joints_[node.id]['axis']
                        if 'limit_lower' in joints_[node.id]:
                            j.limit.lower = joints_[node.id]['limit_lower']
                        if 'limit_upper' in joints_[node.id]:
                            j.limit.upper = joints_[node.id]['limit_upper']
                        if 'parent' in joints_[node.id]:
                            j.parent = joints_[node.id]['parent'] + '_link'
                        if 'child' in joints_[node.id]:
                            j.child = joints_[node.id]['child'] + '_link'
                        if 'origin_xyz' in joints_[node.id]:
                            j.origin.xyz = joints_[node.id]['origin_xyz']
                        if 'origin_rpy' in joints_[node.id]:
                            j.origin.rpy = joints_[node.id]['origin_rpy']
                        if args.no_mimic and 'mimic' in joints_[node.id]:
                            # disable mimic
                            j.joint_type = 'fixed'
                            j.limit = None
                            j.axis = None
                        else:
                            if 'mimic' in joints_[node.id]:
                                j.mimic = JointMimic(
                                    joint_name=joints_[node.id]['mimic'])
                            if 'mimic_multiplier' in joints_[node.id]:
                                j.mimic.multiplier = joints_[
                                    node.id]['mimic_multiplier']
                            if 'mimic_offset' in joints_[node.id]:
                                j.mimic.offset = joints_[
                                    node.id]['mimic_offset']
                #
                # add link and joint
                robot_.add_link(l)
                robot_.add_joint(j)

            retrive_node(node.children, node)
            depth_ -= 1
        elif isinstance(node, scene.GeometryNode):
            # print('writing mesh file to meshes/{}.dae'.format(node.geometry.id))
            # write mesh
            c = Collada()
            g = node.geometry
            n = scene.Node(g.name + '-node', [node])
            s = scene.Scene(g.name + '-scene', [])
            # s.nodes.extend(parent.transforms) # ?? need this?
            s.nodes.append(n)
            cont = asset.Contributor(
                author="Association GUNDAM GLOBAL CHALLENGE",
                comments="This file is automatically generated by " +
                (' '.join(sys.argv)).replace('--', '\-\-') + ' '
                "and distributed under the TERMS OF USE FOR GUNDAM RESEARCH OPEN SIMULATOR Attribution-NonCommercial-ShareAlike",
                copyright="SOTSU, SUNRISE / GUNDAM GLOBAL CHALLENGE",
            )
            c.assetInfo.contributors.append(cont)
            c.geometries.append(g)
            c.materials = [m.target for m in node.materials]
            c.effects = [m.target.effect for m in node.materials]
            c.scenes.append(s)
            c.scene = s
            if args.write_mesh:
                c.write('meshes/{}.dae'.format(g.id))
            #
            # update urdf
            l = [l for l in robot_.links if l.name == parent.id + '_link'][0]
            j = [j for j in robot_.joints if j.name == parent.id + '_joint'][0]
            l.visual = Visual(
                geometry=Mesh(
                    filename='package://gundam_rx78_description/meshes/{}.dae'.format(
                        g.id),
                    scale=[scale_, scale_, scale_]))
            # get bounding box of scene
            l.collision = get_bouding_box(c.geometries)
            l.inertial = calc_inertia(l.collision)

        elif isinstance(node, scene.ExtraNode):
            pass
        else:
            print('skipping {}'.format(node))


# update to human readable joint name
def update_joint_name(robot):
    for j in robot.joints:
        joint_name = j.name[:-len('_joint')]
        if joint_name in joints_ and 'name' in joints_[joint_name]:
            j.name = joints_[joint_name]['name']
        if j.mimic and j.mimic.joint and j.mimic.joint in joints_ and 'name' in joints_[j.mimic.joint]:
            j.mimic.joint = joints_[j.mimic.joint]['name']


#
def add_gazebo_nodes(robot):
    for j in robot.joints:
        if j.joint_type != "revolute":
            continue

        # joint parent and children needs physical properties
        for l in [l for l in robot.links if l.name in [j.parent, j.child]]:
            g = etree.Element('gazebo', reference=l.name)
            etree.SubElement(g, 'selfCollide').text = 'false'
            # etree.SubElement(g, 'mu1').text = '0.2'
            # etree.SubElement(g, 'mu2').text = '0.2'
            etree.SubElement(g, 'mu1').text = '9000'
            etree.SubElement(g, 'mu2').text = '1.5'
            # sole links ** GGC HACK
            if l.name in ["rx78_object_034_link", "rx78_object_091_link", 'rx78_object_089_link', 'rx78_object_032_link']:
                etree.SubElement(g, 'kp').text = '100000.0'
                etree.SubElement(g, 'kd').text = '100.0'
                etree.SubElement(g, 'fdir1').text = '1 0 0'
                etree.SubElement(g, 'maxVel').text = '1.0'
                etree.SubElement(g, 'minDepth').text = '0.001'
            robot.add_aggregate('gazebo', g)

            # avoid null link for crotch_p ** GGC HACK
            if l.name == 'rx78_Null_035_link':
                l.collision = Collision(origin=Pose(xyz=[-0.5, 0, 0]), geometry=Box(size=[1.0, 0.8, 0.8]))
                l.inertial = calc_inertia(l.collision, 400)
            if l.name == 'rx78_Null_085_link':
                l.collision = Collision(origin=Pose(xyz=[0.5, 0, 0]), geometry=Box(size=[1.0, 0.8, 0.8]))
                l.inertial = calc_inertia(l.collision, 400)

            if l.collision is None:
                l.collision = Collision(geometry=Box(size=[0.2, 0.2, 0.2]))
            if l.inertial is None:
                l.inertial = calc_inertia(l.collision)

        # actuated joint
        if not args.no_mimic or j.mimic is None:
            # add extra info for actuated joints
            g = etree.Element('gazebo', reference=j.name)
            etree.SubElement(g, 'provideFeedback').text = '1'
            etree.SubElement(g, 'implicitSpringDamper').text = '1'
            robot.add_aggregate('gazebo', g)
            # add transmission
            trans = Transmission()
            trans.name = j.name + '_trans'
            joi = TransmissionJoint(j.name)
            if args.controller_type == 'position':
                joi.add_aggregate(
                    'hardwareInterface', 'hardware_interface/PositionJointInterface')
            if args.controller_type == 'velocity':
                joi.add_aggregate(
                    'hardwareInterface', 'hardware_interface/VelocityJointInterface')
            if args.controller_type == 'effort':
                joi.add_aggregate(
                    'hardwareInterface', 'hardware_interface/EffortJointInterface')
            act = Actuator(j.name + '_motor')
            act.mechanicalReduction = 1.0
            trans.add_aggregate('joint', joi)
            trans.add_aggregate('actuator', act)
            trans.type = "transmission_interface/SimpleTransmission"
            robot.add_aggregate('transmission', trans)

    # GGC HACK
    for l in robot.links:
        # elbow_p center of mass and joint axis needs displacement
        if l.name in ['rx78_object_076_link', 'rx78_object_062_link']:
            l.inertial.origin.xyz[2] += -1.0
            l.inertial.mass = l.inertial.mass * 1.5
        # knee_p
        if l.name in ['rx78_object_023_link', 'rx78_object_041_link']:
            l.inertial.origin.xyz[2] += -1.25
            l.inertial.mass = l.inertial.mass * 1.5
        # ankle_r
        # if l.name in ['rx78_object_089_link', 'rx78_object_032_link']: # back sole
        #     l.inertial.origin.xyz[0] +=  0.55
        #     l.inertial.origin.xyz[2] += -0.35
        #     l.inertial.mass = l.inertial.mass*5
        # if l.name in ['rx78_object_034_link', 'rx78_object_091_link']: # front sole
        #     l.inertial.origin.xyz[0] -=  0.4
        #     l.inertial.origin.xyz[2] += -0.6
        # ankle cover
        if l.name in ['rx78_object_021_link', 'rx78_object_039_link']:  # ankle cover
            l.inertial.origin.xyz[1] -= 0.8
            l.inertial.origin.xyz[2] += 0.5

    # for urdfdom_py = 0.4.0
    # Once https://github.com/ros/urdf_parser_py/pull/47 is merged, we can remove this block
    from rospkg import RosPack
    if RosPack().get_manifest('urdfdom_py').version == '0.4.0':
        for l in robot.links:
            if l.visual:
                l.add_aggregate('visual', l.visual)
            if l.collision:
                l.add_aggregate('collision', l.collision)

    robot.add_aggregate('gazebo', etree.fromstring('<gazebo>'
                                                   '<plugin filename="libgazebo_ros_control.so" name="gazebo_ros_control">'
                                                   '<robotNamespace>/</robotNamespace>'
                                                   '<robotSimType>gazebo_ros_control/DefaultRobotHWSim</robotSimType>'
                                                   '<legacyModeNS>true</legacyModeNS>'
                                                   '</plugin>'
                                                   '<plugin name="ground_truth" filename="libgazebo_ros_p3d.so">'
                                                   '<frameName>world</frameName>'
                                                   '<bodyName>base_link</bodyName>'
                                                   '<topicName>base_link_ground_truth</topicName>'
                                                   '<updateRate>30.0</updateRate>'
                                                   '</plugin>'
                                                   '</gazebo>'))


# write urdf file
def write_urdf_file(name, robot):
    f = open('urdf/{}.urdf'.format(name), 'w')
    print("writing urdf file to %s" % f.name)
    f.write(
        '<?xml version="1.0" ?>\n'
        '<!--\n'
        '  This file is automatically generated by ' + (' '.join(sys.argv)).replace('--', '\-\-') + '\n'
        '  and distributed under the TERMS OF USE FOR GUNDAM RESEARCH OPEN SIMULATOR Attribution-NonCommercial-ShareAlike\n'
        '  Copyright: SOTSU, SUNRISE / GUNDAM GLOBAL CHALLENGE\n'
        '-->\n')
    f.write(robot.to_xml_string().split("\n", 1)[1])  # skip <?xml version="1.0" ?>
    f.close()


# write ros_control configuration file
def write_control_file():
    # write control file
    f = open('../gundam_rx78_control/config/gundam_rx78_control.yaml', 'w')
    print("Writing ros_control config file to %s" % f.name)
    f.write('# Publish all joint states -----------------------------------\n'
            'joint_state_controller:\n'
            '  type: joint_state_controller/JointStateController\n'
            '  publish_rate: 50\n'
            '\n')
    f.write('# Position Controllers ---------------------------------------\n')
    for i, j in joints_.items():
        if 'name' in j:
            f.write('%s_position:\n' % j['name'])
            f.write('  type: %s_controllers/JointPositionController\n' %
                    args.controller_type)
            f.write('  joint: %s\n' % j['name'])
            if 'pid' in j:
                f.write('  pid: {p: %f, i: %f, d: %f}\n' % (j['pid']['p'], j['pid']['i'], j['pid']['d']))
            else:
                f.write('  pid: {p: %f, i: %f, d: %f}\n' % (default_pid['p'], default_pid['i'], default_pid['d']))
            # for mimic joints
            if not args.no_mimic:
                has_mimic_joints = False
                for ii, jj in joints_.items():
                    if 'mimic' in jj and jj['mimic'] == i:
                        if not has_mimic_joints:
                            f.write('  mimic_joints:\n')
                            has_mimic_joints = True
                        f.write('    %s_joint_position:\n' % ii)
                        f.write('      type: %s_controllers/JointPositionController\n' % args.controller_type)
                        f.write('      joint: %s_joint\n' % ii)
                        if 'pid' in jj:
                            f.write('      pid: {p: %f, i: %f, d: %f}\n' % (jj['pid']['p'], jj['pid']['i'], jj['pid']['d']))
                        elif 'pid' in j:
                            f.write('      pid: {p: %f, i: %f, d: %f}\n' % (j['pid']['p'], j['pid']['i'], j['pid']['d']))
                        else:
                            f.write('      pid: {p: %f, i: %f, d: %f}\n' % (default_pid['p'], default_pid['i'], default_pid['d']))

    f.write('\n')
    f.write('# Joint Trajectory Controllers ---------------------------------------\n')
    f.write('fullbody_controller:\n')
    f.write('#  type: %s_controllers/JointTrajectoryController\n' % args.controller_type)
    f.write('  type: gundam_rx78_control/JointTrajectoryController\n')
    f.write('  joints:\n')
    for i, j in joints_.items():
        if 'name' in j:
            f.write('    - %s\n' % j['name'])
    # for mimic joints
    if not args.no_mimic:
        f.write('  mimic_joints:\n')
        for i, j in joints_.items():
            if 'mimic' in j:
                f.write('    - %s_joint # %s\n' % (i, joints_[j['mimic']]['name']))
    # gains
    f.write('  gains:\n')
    for i, j in joints_.items():
        if 'name' in j:
            if 'pid' in j:
                f.write('    %s : {p: %f, i: %f, d: %f}\n' % (j['name'], j['pid']['p'], j['pid']['i'], j['pid']['d']))
            else:
                f.write('    %s : {p: %f, i: %f, d: %f}\n' % (j['name'], default_pid['p'], default_pid['i'], default_pid['d']))
    # for mimic joints
    if not args.no_mimic:
        for i, j in joints_.items():
            if 'mimic' in j:
                if 'pid' in j:
                    f.write('    %s_joint : {p: %f, i: %f, d: %f}' % (i, j['pid']['p'], j['pid']['i'], j['pid']['d']))
                elif 'pid' in joints_[j['mimic']]:
                    jj = joints_[j['mimic']]
                    f.write('    %s_joint : {p: %f, i: %f, d: %f}' % (i, jj['pid']['p'], jj['pid']['i'], jj['pid']['d']))
                else:
                    f.write('    %s_joint : {p: %f, i: %f, d: %f}' % (i, default_pid['p'], default_pid['i'], default_pid['d']))
                f.write('    # mimic joint of %s_joint\n' % (joints_[j['mimic']]['name']))
    f.write('  constraints:\n')
    f.write('    goal_time: 0.6\n')
    f.write('    stopped_velocity_tolerance: 0.05\n')
    f.write('    # joint: {trajectory: 0.2, goal: 0.2}\n')
    f.write('  stop_trajectory_duration: 0.5\n')
    f.write('  state_publish_rate:  125\n')
    f.write('  action_monitor_rate: 10\n')

global robot, args
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help='input collada file name')
    parser.add_argument('--controller_type', choices=[
                        'position', 'velocity', 'effort'], default='effort', help='set controller type')
    parser.add_argument(
        '--no_mimic', action='store_true', help='disable mimic joint')
    parser.add_argument(
        '--pin', action='store_true', help='pin the robot to the world')
    parser.add_argument(
        '--write_mesh', action='store_true', help='write mech files')
    args = parser.parse_args()

    # load collada file
    mesh_ = Collada(args.input_file)
    if mesh_.xmlnode.getroot().attrib['version'] != '1.4.1':
        print('This program only support COLLADA 1.4.1, but the input file is %s' %
              mesh_.xmlnode.getroot().attrib['version'])
        sys.exit(1)

    # extract robot name
    name_ = os.path.splitext(os.path.basename(mesh_.filename))[0]

    # create robot instance
    robot_ = Robot(name=name_)
    # DEBUG: create pinned model
    if args.pin:
        robot_.add_link(Link(name='world'))
        robot_.add_joint(
            Joint(name='world_to_base', parent='world', child='base_link', joint_type='fixed'))
    robot_.add_link(Link(name='base_link'))
    print("loaded collada file {}".format(name_))
    # retrive_node(mesh_.scene.nodes)
    # retrive_node(mesh_.scene.nodes[1].children[0].children) # hack for base_link
    # retrive_node(mesh_.scene.nodes[1].children) # hack for base_link
    retrive_node(mesh_.scene.nodes[0].children)  # hack for base_link

    print('all weight is %f' % all_weight_)

    # update transmission joints to human readable ones
    update_joint_name(robot_)

    # add gazebo information
    add_gazebo_nodes(robot_)

    # write urdf file
    write_urdf_file(name_, robot_)

    # write control file
    write_control_file()
