import numpy as np
from tqdm import tqdm
import seaborn as sns

# from agents import SublevelSafeSet, MobileAgent, GoalPursuing
# from models import SharedGoalsSCARA, BayesianHumanBall
# from utils.Record import Record


if __name__ == "__main__":
    path = "../data/simulated_safe_prob.npz"
    with np.load(path) as data:
        safe_prob = data['safe_prob']

    print(safe_prob.shape)
    # print(safe_prob[0,0,:,:])
    print(safe_prob)

    p1 = sns.heatmap(safe_prob[0, 0, :, :])
    fig = p1.get_figure()
    fig.show()
    fig.savefig('heatmap.png')