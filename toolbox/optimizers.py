'''
Custom optimizers
'''

import torch
import torch.nn as nn
import torch.nn.functional as F
import logging

EPS = 1e-7

def get_optim_parameters(model):
    for param in model.parameters():
        yield param

def get_optimizer_scheduler(experience,parameters,losses = None):
    log = logging.getLogger("main")

    if 'sgd' == parameters.optimizer:
        optimizer = torch.optim.SGD([experience.input_image.requires_grad_()],
                            lr=parameters.lr,
                            momentum=parameters.momentum,
                            weight_decay=parameters.weight_decay
                            )
    elif 'adam' == parameters.optimizer:
        optimizer = torch.optim.Adam([experience.input_image.requires_grad_()],
                            lr=parameters.lr,
                            amsgrad=False)
    elif 'lbfgs' == parameters.optimizer:
        optimizer = torch.optim.LBFGS([experience.input_image.requires_grad_()],
                            lr=parameters.lr)
    elif 'rmsprop' == parameters.optimizer:
        optimizer = torch.optim.RMSprop([experience.input_image.requires_grad_()],
                            lr=parameters.lr,
                            weight_decay = parameters.weight_decay,
                            momentum = parameters.momentum)
    
    else:
        raise 'Optimizer {} not available'.format(parameters.optimizer)


    if 'step' == parameters.scheduler:
        log.info(f' --- Setting lr scheduler to StepLR ---')
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=parameters.lr_step, gamma=parameters.lr_decay)
    elif 'exponential' == parameters.scheduler:
        log.info(f' --- Setting lr scheduler to ExponentialLR ---')
        scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer, gamma=parameters.lr_decay)    
    elif 'plateau' == parameters.scheduler:
        if losses is None:
            raise Exception("Losses must be provided for plateau loss to work")
        log.info(f' --- Setting lr scheduler to ReduceLROnPlateau ---') 
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', factor=parameters.lr_decay, patience=parameters.lr_step)
        scheduler = PlateauScheduling(scheduler,losses)
    elif 'adjusted' == parameters.scheduler:
        scheduler = Adjust_lr(experience,optimizer,parameters)
    elif 'none' == parameters.scheduler:
        scheduler = EmptyScheduler()
    else:
        raise f'Scheduler {parameters.scheduler} not available'
    
    return optimizer,scheduler


class PlateauScheduling():
    # this class is made only because not all schedulers have the same step function (Plateau requires a "metrics" argument)
    # we don't want the specificiy to appear in our code. We thus encapsulate these schedulers by defining a default step function inside this class

    def __init__(self,scheduler, losses):
        self.scheduler = scheduler
        self.value = losses.total_loss
    
    def step(self):
        self.scheduler.step(self.value())


class Adjust_lr():

    def __init__(self,experience,optimizer,parameters):
        """Sets the learning rate to the initial LR decayed by 10 every experience.step epochs"""
        self.optimizer = optimizer
        self.experience = experience
        self.base_lr = parameters.lr
        self.lr_step = parameters.lr_step

    def step(self):
        lr = self.base_lr * (0.1 ** (self.experience.epoch // self.lr_step))
        for i in range(len(self.optimizer.param_groups)):
            self.optimizer.param_groups[i]['lr'] = lr

class EmptyScheduler():

    def __init__(self):
        pass
    
    def step(self):
        pass

