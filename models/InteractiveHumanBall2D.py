from .KinematicModel import KinematicModel
import numpy as np
from numpy.matlib import repmat
from numpy import zeros, eye, ones, matrix
from numpy.random import rand, randn
from numpy.linalg import norm, inv
from numpy import cos, sin, arccos, sqrt, pi, arctan2
from panda3d.core import *
from direct.gui.DirectGui import *

class InteractiveHumanBall2D(KinematicModel):

    max_v = 2
    max_a = 4

    def __init__(self, agent, dT, auto=True, init_state=[5,5,0,0]):
        KinematicModel.__init__(self, init_state, agent, dT, auto, is_2D = True)
        self.goals[2,:] = zeros(100)
        self.goal = np.vstack(self.goals[:,0])

    def init_x(self, init_state):
        x = np.vstack(init_state)
        self.x = matrix(zeros((4,1)))
        self.set_P(x[[0,1]])
        self.set_V(x[[2,3]])
        
        self.u = matrix(zeros((2,1)))

    def set_saturation(self):
        self.max_u =  matrix([[self.max_a], [self.max_a]])
        self.min_u = -matrix([[self.max_a], [self.max_a]])
        self.max_x =  matrix([np.inf, np.inf, self.max_v, self.max_v]).T
        self.min_x = -matrix([np.inf, np.inf, self.max_v, self.max_v]).T

    def estimate_state(self, obstacle):
        self.kalman_estimate_state()
 
    def get_P(self):
        return np.vstack([self.x[[0,1]], 0]);
    
    def get_V(self):
        return np.vstack([self.x[[2,3]], 0]);

    def get_PV(self):
        return np.vstack([self.get_P(), self.get_V()])

    def get_closest_X(self, Xh):
        self.m = self.get_PV()
        return self.m

    def set_P(self, p):
        self.x[0,0] = p[0];
        self.x[1,0] = p[1];

    def set_V(self, v):
        self.x[2,0] = v[0];
        self.x[3,0] = v[1];

    def A(self):
        A = matrix(eye(4,4));
        A[0,2] = self.dT;
        A[1,3] = self.dT;
        return A;

    def B(self):
        B = matrix(zeros((4,2)));
        B[0,0] = self.dT**2/2;
        B[1,1] = self.dT**2/2;
        B[2,0] = self.dT;
        B[3,1] = self.dT;
        return B;

    def p_M_p_X(self): # p closest point p X
        ret = zeros((6,4))
        ret[0,0] = 1
        ret[1,1] = 1
        ret[3,2] = 1
        ret[4,3] = 1
        return ret

    def u_ref(self):
        K = matrix([[1,0,2,0],[0,1,0,2]]);
        dp = self.observe(self.goal[[0,1]] - self.m[[0,1]]);
        dis = norm(dp);
        v = self.observe(self.m[[3,4]]);

        if dis > 1.5:
            u0 = dp / max(abs(dp)) * self.max_a;
        else:
            u0 = - K*(self.m[[0,1,3,4]] - self.goal[[0,1,3,4]]);

        u0 = u0 + randn() * 0.05
        return u0;

    def load_model(self, render, loader, color=[0.8, 0.3, 0.2, 0.8], scale=0.5):
        self.render = render
        self.human_sphere = self.add_sphere(list(self.get_P()[:,0]), [0.8, 0.3, 0.2, 0.8], scale)
        self.human_goal_sphere = self.add_sphere([self.goal[0], self.goal[1],0], [0.8, 0.3, 0.2, 0.5], scale)
    
    def redraw_model(self):
        self.human_sphere.setPos(self.get_P()[0], self.get_P()[1], 0)
        self.human_goal_sphere.setPos(self.goal[0], self.goal[1], 0)
        
    
    def model_auxiliary(self):
        if not hasattr(self, 'human_v'):
            [self.human_v, self.human_u] = self.draw_movement(list(self.get_PV()[:,0]), list(self.u[:,0])+[0])
        else:

            self.move_seg(self.human_u, np.array(self.get_P()).reshape(-1,).tolist(), np.array(self.u).reshape(-1,).tolist()+[0])
            self.move_seg(self.human_v, np.array(self.get_P()).reshape(-1,).tolist(), np.array(self.get_V()).reshape(-1,).tolist())

