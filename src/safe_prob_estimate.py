import numpy as np
from tqdm import tqdm

from agents import SublevelSafeSet, MobileAgent, GoalPursuing
from models import SharedGoalsSCARA, BayesianHumanBall
from utils.Record import Record


def simulate_interaction(horizon=200, h_init_state = [0, 0, 0, 0], r_init_state = [0, 0, 0, 0]):
    fps = 20
    dT = 1 / fps

    # goals are randomly initialized inside objects
    ## TODO: use non-cooperative human and goal pursuing robot for safety probability
    ## TODO: set initial state for human and robot (probably human's goal or other history-related info?)

    h_init_state = [0, 0, 1, 0, 0, 0]
    r_init_state = [-2, -2, 0, 1, 0, 0]

    # robot = SharedGoalsSCARA(SublevelSafeSet(), dT)
    # robot = SharedGoalsSCARA(GoalPursuing(), dT, init_state=r_init_state, use_intent_pred=True) # goal pursuing robot # calc_control_input() missing 1 required positional argument: 'max_u'
    robot = SharedGoalsSCARA(SublevelSafeSet(), dT, init_state=r_init_state, use_intent_pred=True)  # TODO: goal pursuing robot
    human = BayesianHumanBall(MobileAgent, dT, init_state=h_init_state)
    robot.set_partner_agent(human)
    human.set_partner_agent(robot)

    # print(robot.hist_len) # int: 5
    r_hist = np.zeros((robot.hist_len, 4))
    h_hist = np.zeros((robot.hist_len, 4))

    for i in range(robot.hist_len):
        r_hist[i, :] = [r_init_state[0]-(robot.hist_len-i-1)*r_init_state[2]*dT, r_init_state[1]-(robot.hist_len-i-1)*r_init_state[3]*dT, r_init_state[2], r_init_state[3]]
        h_hist[i, :] = [h_init_state[0]-(robot.hist_len-i-1)*h_init_state[2]*dT, h_init_state[1]-(robot.hist_len-i-1)*h_init_state[3]*dT, h_init_state[2], h_init_state[3]]

        r_hist_mat = np.asmatrix(r_hist[i, :]).transpose()
        h_hist_mat = np.asmatrix(h_hist[i, :]).transpose()

        # all valid trajs
        # print('h_hist[i, :] ')
        # print(h_hist[i, :])
        # print('r_hist[i, :]')
        # print(r_hist[i, :])

        robot.intention_data["xh_hist"].append(h_hist_mat)
        if len(robot.intention_data["xh_hist"]) > robot.hist_len:
            robot.intention_data["xh_hist"].popleft()
        robot.intention_data["xr_hist"].append(r_hist_mat)
        if len(robot.intention_data["xr_hist"]) > robot.hist_len:
            robot.intention_data["xr_hist"].popleft()
        robot.intention_data["goals_hist"].append(robot.possible_goals[0:4, :]) ## TODO: need double-check
        if len(robot.intention_data["goals_hist"]) > robot.hist_len:
            robot.intention_data["goals_hist"].popleft()

    # print(robot.intention_data["goals_hist"])

    xh_traj = np.zeros((human.n, horizon))
    xr_traj = np.zeros((robot.n, horizon))
    possible_goals = np.zeros((*human.possible_goals.shape, horizon))
    h_goals = np.zeros((human.goal.shape[0], horizon))
    r_goals = np.zeros((robot.goal.shape[0], horizon))
    h_goal_reached = np.zeros(horizon)
    h_goal_idx = np.zeros(horizon)

    for i in range(horizon):
        # save data
        xh_traj[:, [i]] = human.x
        xr_traj[:, [i]] = robot.x
        possible_goals[:, :, i] = human.possible_goals
        h_goals[:, [i]] = human.goal
        r_goals[:, [i]] = robot.goal
        h_goal_reached[i] = int(human.is_goal_reached())
        h_goal_idx[i] = np.argmin(np.linalg.norm(human.possible_goals - human.goal, axis=0))

        # move both agents
        human.update(robot)
        human.move()
        robot.update(human)
        robot.move()

    collision_cnt = 0
    if robot.score['collision_cnt'] > 0:
        collision_cnt = 1

    return xh_traj, xr_traj, possible_goals, h_goal_reached, h_goal_idx, collision_cnt


def propogate_goal_reached(h_goal_reached, h_goal_idx):
    goal_idxs = np.zeros_like(h_goal_idx)
    # propogate backwards the index of the reached goal to the previous time steps
    goals_reached = np.where(h_goal_reached)[0]
    if len(goals_reached) > 0:
        curr_goal = h_goal_idx[goals_reached[-1]]

        # cheat a bit and use the actual human goal for any remaining time steps
        goal_idxs[goals_reached[-1]:] = h_goal_idx[goals_reached[-1]:]

        for i in range(goals_reached[-1], -1, -1):
            if h_goal_reached[i] == 1:
                curr_goal = h_goal_idx[i]
            goal_idxs[i] = curr_goal
    return goal_idxs


def create_dataset(n_trajectories=1):
    horizon = 200

    all_xh_traj = []
    all_xr_traj = []
    all_goals = []
    all_h_goal_reached = []

    # labels
    goal_reached = []
    goal_idx = []

    ## TODO: add robot goal reached. Done for now. This is only required during the testing phase
    ## TODO: add safety score. Done

    all_collision_cnt = 0.0;

    for i in tqdm(range(n_trajectories)):
        xh_traj, xr_traj, goals, h_goal_reached, h_goal_idx, collision_cnt = simulate_interaction(horizon=horizon)
        h_goal_idx = propogate_goal_reached(h_goal_reached, h_goal_idx)

        # if this is the first iteration, initialize the arrays
        if i == 0:
            all_xh_traj = np.zeros((*xh_traj.shape, n_trajectories))
            all_xr_traj = np.zeros((*xr_traj.shape, n_trajectories))
            all_goals = np.zeros((*goals.shape, n_trajectories))
            all_h_goal_reached = np.zeros((*h_goal_reached.shape, n_trajectories))
            goal_reached = np.zeros((1, n_trajectories))
            goal_idx = np.zeros((*h_goal_idx.shape, n_trajectories))

        all_xh_traj[:, :, i] = xh_traj
        all_xr_traj[:, :, i] = xr_traj
        all_goals[:, :, :, i] = goals
        all_h_goal_reached[:, i] = h_goal_reached
        goal_reached[:, i] = h_goal_reached[-1]
        goal_idx[:, i] = h_goal_idx

        all_collision_cnt += collision_cnt

    safe_prob = 1 - all_collision_cnt/n_trajectories

    return all_xh_traj, all_xr_traj, all_goals, all_h_goal_reached, goal_reached, goal_idx, safe_prob


def get_safe_prob(n_trajectories=1):
    horizon = 200

    all_collision_cnt = 0.0;

    safe_prob = np.zeros([2,2,2,2])

    init = []

    for hx in range(2):
        for hy in range(2):
            for rx in range(2):
                for ry in range(2):
                    init = [init, np.array(hx, hy, rx, ry)]


                    all_collision_cnt = 0.0

                    for i in tqdm(range(n_trajectories)):
                        xh_traj, xr_traj, goals, h_goal_reached, h_goal_idx, collision_cnt = simulate_interaction(
                            horizon=horizon, h_init_state=[hx*0.5+1, hy*0.5+1, -1, 0], r_init_state=[rx*0.5, ry*0.5, 1, 1])
                        # h_goal_idx = propogate_goal_reached(h_goal_reached, h_goal_idx)

                        all_collision_cnt += collision_cnt

                    safe_prob[hx,hy,rx,ry] = 1 - all_collision_cnt/n_trajectories

    return safe_prob


def save_data(path="../data/simulated_interactions.npz", n_trajectories=10):
    all_xh_traj, all_xr_traj, all_goals, all_h_goal_reached, goal_reached, goal_idx, safe_prob = create_dataset(
        n_trajectories=n_trajectories)

    safe_prob = get_safe_prob(n_trajectories=n_trajectories)
    print(safe_prob)

    np.savez(path, xh_traj=all_xh_traj, xr_traj=all_xr_traj, goals=all_goals, h_goal_reached=all_h_goal_reached,
             goal_reached=goal_reached, goal_idx=goal_idx)

    # TODO: save data using pickle, as in generate_data.py for visualization


def get_data(path="../data/simulated_safe_prob.npz", n_trajectories=10):
    safe_prob = get_safe_prob(n_trajectories=n_trajectories)
    np.savez(path, safe_prob=safe_prob)
    print(safe_prob)


if __name__ == "__main__":
    # save_data("mfi_data/simulated_interactions_train.npz", n_trajectories=10)
    get_data(path="../data/simulated_safe_prob_2.npz", n_trajectories=10)
    # save_data("../data/simulated_interactions_test.npz", n_trajectories=200)
