#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
# Andre Anjos <andre.dos.anjos@gmail.com>
# Thu 14 Jul 17:52:14 2011 

"""Tests for RProp MLP training.
"""

import os, sys
import unittest
import torch

def rmse(output, target):
  """Evaluates the mean-square error between outputs and targets."""
  return ((output - target)**2).transpose(1,0).partial_mean().sqrt()

class PythonRProp:
  """A simplified (and slower) version of RProp training written in python.
  
  This version of the code is probably easier to understand than the C++
  version. Both algorithms should, essentially, be the same, except for the
  performance for obvious reasons.
  """

  def __init__(self, train_biases=True):
    # Our state
    self.DW = None #delta matrixes for weights
    self.DB = None #delta matrixes for biases
    self.PDW = None #partial derivatives for weights
    self.PDB = None #partial derivatives for biases
    self.PPDW = None #previous partial derivatives for weights
    self.PPDB = None #previous partial derivatives for biases
    self.train_biases = train_biases

  def reset(self):
    """Resets our internal state"""

    self.DW = None #delta matrixes for weights
    self.DB = None #delta matrixes for biases
    self.PDW = None #partial derivatives for weights
    self.PDB = None #partial derivatives for biases
    self.PPDW = None #previous partial derivatives for weights
    self.PPDB = None #previous partial derivatives for biases

  def train(self, machine, input, target):

    def sign(x):
      """A handy sign function"""
      if (x == 0): return 0
      if (x < 0) : return -1
      return +1
    
    # some constants for RProp
    DELTA0 = 0.1
    DELTA_MIN = 1e-6
    DELTA_MAX = 50
    ETA_MINUS = 0.5
    ETA_PLUS = 1.2

    W = machine.weights #weights
    B = machine.biases #biases
    
    #simulated bias input...
    BI = [torch.core.array.float64_1(input.extent(0)) for k in B]
    for k in BI: k.fill(1)

    #state
    if self.DW is None: #first run or just after a reset()
      self.DW = [k.empty_like() for k in W]
      for k in self.DW: k.fill(DELTA0)
      self.DB = [k.empty_like() for k in B]
      for k in self.DB: k.fill(DELTA0)
      self.PPDW = [k.empty_like() for k in W]
      for k in self.PPDW: k.fill(0)
      self.PPDB = [k.empty_like() for k in B]
      for k in self.PPDB: k.fill(0)

    # Instantiate partial outputs and errors
    O = [None for k in B]
    O.insert(0, input) # an extra slot for the input
    E = [None for k in B]

    # Feeds forward
    for k in range(len(W)):
      O[k+1] = torch.math.prod(O[k], W[k])
      for sample in range(O[k+1].extent(0)):
        O[k+1][sample,:] += B[k]
      O[k+1] = O[k+1].tanh()
      print "Output[%d]" % (k+1), O[k+1]

    # Feeds backward
    E[-1] = (1-(O[-1]**2)) * (O[-1] - target) #last layer
    print "Error[-1]", E[-1]
    for k in reversed(range(len(W)-1)): #for all remaining layers
      E[k] = (1-(O[k]**2)) * torch.math.prod(E[k+1], W[k].transpose(1,0))
      print "Error[%d]" % k, E[k]

    # Calculates partial derivatives, accumulate
    self.PDW = [torch.math.prod(O[k].transpose(1,0), E[k]) for k in range(len(W))]
    for i, k in enumerate(self.PDW): print "PDW[%d]: %s" % (i, k)
    self.PDB = [torch.math.prod(BI[k], E[k]) for k in range(len(W))]
    for i, k in enumerate(self.PDB): print "PDB[%d]: %s" % (i, k)

    # Updates weights and biases
    WUP = [i * j for (i,j) in zip(self.PPDW, self.PDW)]
    BUP = [i * j for (i,j) in zip(self.PPDB, self.PDB)]

    # Iterate over each weight and bias and see what to do:
    for k, up in enumerate(WUP):
      for i in range(up.extent(0)):
        for j in range(up.extent(1)):
          if up[i,j] > 0:
            self.DW[k][i,j] = min(self.DW[k][i,j]*ETA_PLUS, DELTA_MAX)
            W[k][i,j] -= sign(self.PDW[k][i,j]) * self.DW[k][i,j]
            self.PPDW[k][i,j] = self.PDW[k][i,j]
          elif up[i,j] < 0:
            self.DW[k][i,j] = max(self.DW[k][i,j]*ETA_MINUS, DELTA_MIN)
            self.PPDW[k][i,j] = 0
          elif up[i,j] == 0:
            W[k][i,j] -= sign(self.PDW[k][i,j]) * self.DW[k][i,j]
            self.PPDW[k][i,j] = self.PDW[k][i,j]
    machine.weights = W

    if self.train_biases:
      for k, up in enumerate(BUP):
        for i in range(up.extent(0)):
          if up[i] > 0:
            self.DB[k][i] = min(self.DB[k][i]*ETA_PLUS, DELTA_MAX)
            B[k][i] -= sign(self.PDB[k][i]) * self.DB[k][i]
            self.PPDB[k][i] = self.PDB[k][i]
          elif up[i] < 0:
            self.DB[k][i] = max(self.DB[k][i]*ETA_MINUS, DELTA_MIN)
            self.PPDB[k][i] = 0
          elif up[i] == 0:
            B[k][i] -= sign(self.PDB[k][i]) * self.DB[k][i]
            self.PPDB[k][i] = self.PDB[k][i]
      machine.biases = B

    else:
      machine.biases = 0

class RPropTest(unittest.TestCase):
  """Performs various RProp MLP training tests."""

  def test01_Initialization(self):

    # Initializes an MLPRPropTrainer and checks all seems consistent
    # with the proposed API.
    machine = torch.machine.MLP((4, 1))
    B = 10
    trainer = torch.trainer.MLPRPropTrainer(machine, B)
    self.assertEqual( trainer.batchSize, B )
    self.assertTrue ( trainer.isCompatible(machine) )
    self.assertTrue ( trainer.trainBiases )

    machine = torch.machine.MLP((7, 2))
    self.assertFalse ( trainer.isCompatible(machine) )

    trainer.trainBiases = False
    self.assertFalse ( trainer.trainBiases )

  def test02_SingleLayerNoBiasControlled(self):

    # Trains a simple network with one single step, verifies
    # the training works as expected by calculating the same
    # as the trainer should do using python.
    machine = torch.machine.MLP((4, 1))
    machine.biases = 0
    w0 = torch.core.array.array([[.1],[.2],[-.1],[-.05]])
    machine.weights = [w0]
    trainer = torch.trainer.MLPRPropTrainer(machine, 1)
    trainer.trainBiases = False
    d0 = torch.core.array.array([[1., 2., 0., 2.]])
    t0 = torch.core.array.array([[1.]])

    # trains in python first
    pytrainer = PythonRProp(train_biases=trainer.trainBiases)
    pymachine = torch.machine.MLP(machine) #a copy
    pytrainer.train(pymachine, d0, t0)

    # trains with our C++ implementation
    trainer.train_(machine, d0, t0)
    self.assertTrue( (pymachine.weights[0] == machine.weights[0]).all() )

    # a second passage
    d0 = torch.core.array.array([[4., 0., -3., 1.]])
    t0 = torch.core.array.array([[2.]])
    pytrainer.train(pymachine, d0, t0)
    trainer.train_(machine, d0, t0)
    self.assertTrue( (pymachine.weights[0] == machine.weights[0]).all() )

    # a third passage
    d0 = torch.core.array.array([[-0.5, -9.0, 2.0, 1.1]])
    t0 = torch.core.array.array([[3.]])
    pytrainer.train(pymachine, d0, t0)
    trainer.train_(machine, d0, t0)
    self.assertTrue( (pymachine.weights[0] == machine.weights[0]).all() )

  def test03_FisherNoBias(self):
    
    # Trains single layer MLP to discriminate the iris plants from
    # Fisher's paper. Checks we get a performance close to the one on
    # that paper.

    machine = torch.machine.MLP((4, 1))
    machine.randomize()
    machine.biases = 0
    trainer = torch.trainer.MLPRPropTrainer(machine, 10)
    trainer.trainBiases = False

    # A helper to select and shuffle the data
    targets = [ #we choose the approximate Fisher response!
        torch.core.array.array([-2.0]), #setosa
        torch.core.array.array([1.5]), #versicolor
        torch.core.array.array([0.5]), #virginica
        ]
    S = torch.trainer.DataShuffler(torch.db.iris.data().values(), targets)

    # trains in python first
    pytrainer = PythonRProp(train_biases=trainer.trainBiases)
    pymachine = torch.machine.MLP(machine) #a copy

    # We now iterate for several steps, look for the convergence
    for k in range(5):
      print "Iteration %d..." % k
      input, target = S(30)
      pytrainer.train(pymachine, input, target)
      print "Py MSE:", rmse(pymachine(input), target)
      print pymachine
      trainer.train_(machine, input, target)
      print "C++ MSE:", rmse(machine(input), target)
      print machine
      #self.assertTrue( (pymachine.weights[0] == machine.weights[0]).all() )

if __name__ == '__main__':
  sys.argv.append('-v')
  if os.environ.has_key('TORCH_PROFILE') and \
      os.environ['TORCH_PROFILE'] and \
      hasattr(torch.core, 'ProfilerStart'):
    torch.core.ProfilerStart(os.environ['TORCH_PROFILE'])
  os.chdir(os.path.realpath(os.path.dirname(sys.argv[0])))
  unittest.main()
  if os.environ.has_key('TORCH_PROFILE') and \
      os.environ['TORCH_PROFILE'] and \
      hasattr(torch.core, 'ProfilerStop'):
    torch.core.ProfilerStop()

