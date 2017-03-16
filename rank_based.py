#!/usr/bin/python
# -*- encoding=utf-8 -*-
# author: Ian
# e-mail: stmayue@gmail.com
# description: 

import sys
import math
import random
import numpy as np

import binary_heap


class Experience(object):

    def __init__(self, conf):
        self.size = conf['size']
        self.replace_flag = conf['replace_old'] if 'replace_old' in conf else True

        self.alpha = conf['alpha'] if 'alpha' in conf else 0.7
        self.beta_zero = conf['beta_zero'] if 'beta_zero' in conf else 0.5
        self.batch_size = conf['batch_size'] if 'batch_size' in conf else 32
        self.learn_start = conf['learn_start'] if 'learn_start' in conf else 1000

        # http://www.evernote.com/l/ACnDUVK3ShVEO7fDm38joUGNhDik3fFaB5o/
        self.total_steps = conf['steps'] if 'steps' in conf else 100000

        self.index = 0
        self.record_size = 0
        self.isFull = False

        self._experience = {}
        self.priority_queue = binary_heap.BinaryHeap(self.size)

        # P(i) = (rank i) ^ (-alpha) / sum ((rank i) ^ (-alpha))
        pdf = list(
            map(lambda x: math.pow(x, -self.alpha), range(1, self.size + 1))
        )
        pdf_sum = math.fsum(pdf)
        self.power_law_distribution = list(map(lambda x: x / pdf_sum, pdf))


        self.beta_grad = (1 - self.beta_zero) / (self.total_steps - self.learn_start)

    def fix_index(self):
        """
        get next insert index
        :return: index, int
        """
        if self.record_size <= self.size:
            self.record_size += 1
        if self.index % self.size == 0:
            self.isFull = True if len(self._experience) == self.size else False
            if self.replace_flag:
                self.index = 1
                return self.index
            else:
                sys.stderr.write('Experience replay buff is full and replace is set to FALSE!\n')
                return -1
        else:
            self.index += 1
            return self.index

    def store(self, experience):
        """
        store experience, suggest that experience is a tuple of (s1, a, r, s2, t)
        so each experience is valid
        :param experience: maybe a tuple, or list
        :return: bool, indicate insert status
        """
        insert_index = self.fix_index()
        if insert_index > 0:
            if insert_index in self._experience:
                del self._experience[insert_index]
            self._experience[insert_index] = experience
            # add to priority queue
            priority = self.priority_queue.get_max_priority()
            self.priority_queue.update(priority, insert_index)
            return True
        else:
            sys.stderr.write('Insert failed\n')
            return False

    def retrieve(self, indices):
        """
        get experience from indices
        :param indices: list of experience id
        :return: experience replay sample
        """
        return [self._experience[v] for v in indices]

    def rebalance(self):
        """
        rebalance priority queue
        :return: None
        """
        self.priority_queue.balance_tree()

    def update_priority(self, indices, delta):
        """
        update priority according indices and deltas
        :param indices: list of experience id
        :param delta: list of delta, order correspond to indices
        :return: None
        """
        for i in range(0, len(indices)):
            self.priority_queue.update(math.fabs(delta[i]), indices[i])

    def sample(self, global_step):
        """
        sample a mini batch from experience replay
        :param global_step: now training step
        :return: experience, list, samples
        :return: w, list, weights
        :return: rank_e_id, list, samples id, used for update priority
        """
        if self.record_size < self.learn_start:
            sys.stderr.write('Record size less than learn start! Sample failed\n')
            return False, False, False


        distribution = self.power_law_distribution
        rank_list = []
        # sample from k segments
        for n in range(self.batch_size):
            index = random.randint(1, self.priority_queue.size)
            rank_list.append(index)

        # beta, increase by global_step, max 1
        beta = min(self.beta_zero + (global_step - self.learn_start - 1) * self.beta_grad, 1)
        # find all alpha pow, notice that pdf is a list, start from 0
        alpha_pow = [distribution[v - 1] for v in rank_list]
        # w = (N * P(i)) ^ (-beta) / max w
        w = np.power(np.array(alpha_pow) * self.size, -beta)
        w_max = max(w)
        w = np.divide(w, w_max)
        # rank list is priority id
        # convert to experience id
        rank_e_id = 0
        try:
            rank_e_id = self.priority_queue.priority_to_experience(rank_list)
        except:
            print 'a'
        # get experience id according rank_e_id
        experience = self.retrieve(rank_e_id)
        return experience, w, rank_e_id
