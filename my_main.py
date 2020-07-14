import argparse
import tensorflow as tf
import gym
import numpy as np
from ReplayBuffer import PrioritizedReplay, UniformReplay
from agents import DQNAgent, ActorCriticAgent

hyperparams = {
    'gamma': 0.99,
    'copy_step': 25,
    'max_experiences': 10000,
    'min_experiences': 1000,
    'batch_size': 32,
    'learning_rate_dqn': 1e-3,
    'learning_rate_actor': 1e-3,
    'learning_rate_critic': 1e-3,
    'environment': 'Acrobot-v1',
    'hidden_layer_dqn': [128],
    'hidden_layer_actor': [128],
    'hidden_layer_critic': [128],
    'episodes': 100,
    'epsilon': 0.99,
    'min_epsilon': 0.1,
    'decay': 0.9,
}


def start_training_ac():
    env = gym.make(hyperparams['environment'])
    state_spec = len(env.observation_space.sample())
    action_spec = env.action_space.n
    log_name = 'final'
    log_dir = 'logs/acrobotAC/' + log_name
    log_writer = tf.summary.create_file_writer(log_dir)
    agent = ActorCriticAgent(hyperparams['hidden_layer_actor'], hyperparams['hidden_layer_critic'], state_spec,
                             action_spec, hyperparams['learning_rate_actor'], hyperparams['learning_rate_critic'])

    total_rewards = np.empty(hyperparams['episodes'])
    for episode in range(hyperparams['episodes']):
        episode_reward = 0
        done = False
        state = env.reset()
        while not done:
            next_state, reward, done = agent.play_and_train(state, env, hyperparams['gamma'])
            episode_reward += reward
            state = next_state
        total_rewards[episode] = episode_reward
        avg_rewards = total_rewards[max(0, episode - 20):(episode + 1)].mean()
        env.reset()
        with log_writer.as_default():
            tf.summary.scalar('episode reward', episode_reward, step=episode)
            tf.summary.scalar('avg for 100 episodes', avg_rewards, step=episode)


def start_training_dqn(is_prioritized):
    if is_prioritized:
        prio = "Prio"
    else:
        prio = ""

    env = gym.make(hyperparams['environment'])
    state_spec = len(env.observation_space.sample())
    action_spec = env.action_space.n
    log_name = 'final' + prio
    log_dir = 'logs/acrobot/' + log_name

    log_writer = tf.summary.create_file_writer(log_dir)

    epsilon = hyperparams['epsilon']
    buffer = PrioritizedReplay(hyperparams['max_experiences']) if is_prioritized else UniformReplay(
        hyperparams['max_experiences'])

    agent = DQNAgent(hyperparams['hidden_layer_dqn'], state_spec, action_spec, buffer, hyperparams['learning_rate_dqn'],
                     is_prioritized)

    total_rewards = np.empty(hyperparams['episodes'])
    for episode in range(hyperparams['episodes']):
        episode_reward = 0
        epsilon = max(hyperparams['min_epsilon'], epsilon * hyperparams['decay'])
        done = False
        state = env.reset()
        while not done:

            action = agent.play_action(state, epsilon)
            next_state, reward, done, _ = env.step(action)
            episode_reward += reward

            buffer.add((state, action, reward, next_state, done))
            state = next_state

            if len(buffer.experiences) > hyperparams['min_experiences']:
                agent.train(hyperparams['gamma'], hyperparams['batch_size'])

        total_rewards[episode] = episode_reward
        avg_rewards = total_rewards[max(0, episode - 20):(episode + 1)].mean()

        env.reset()
        if episode % 100 == 0:
            print(avg_rewards)

        with log_writer.as_default():
            tf.summary.scalar('episode reward', episode_reward, step=episode)
            tf.summary.scalar('avg for 100 episodes', avg_rewards, step=episode)

    env.close()


def test_model(model):
    env = gym.make(hyperparams['environment'])
    state_spec = len(env.observation_space.sample())
    action_spec = env.action_space.n
    buffer = None
    is_prioritized = False
    is_double = False
    # Create the agent
    agent = DQNAgent(hyperparams['network'], state_spec, action_spec, buffer, hyperparams['learning_rate'],
                     is_prioritized,
                     is_double)
    # Load weights from file
    agent.training_network.load_weights(model)
    obs = env.reset()
    env.render()
    for i in range(20):
        rewards = []
        while True:
            action = agent.play_action(np.atleast_2d(obs)[0], 0.1)
            obs, reward, done, _ = env.step(action)
            env.render()
            rewards.append(reward)
            if done:
                print("Gathered {} reward".format(np.sum(rewards)))
                env.reset()
                break

    env.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', help="One between {train|test}", choices=['train', 'test'], type=str, required=True,
                        dest='mode')
    parser.add_argument('--per', help="Use this if you want experience replay", action="store_true", dest='per',
                        default=False)
    parser.add_argument('--model', help="the model you want to test", type=str, dest='model')
    parser.add_argument('--ac', help="Use actor critic", action="store_true", dest='ac')
    args = parser.parse_args()
    if args.mode == 'train':
        print('TRAIN')
        print("PER", args.per)
        if args.ac:
            start_training_ac()
        else:
            start_training_dqn(args.per)
    elif args.mode == 'test':
        print('test')
        test_model(args.model)
