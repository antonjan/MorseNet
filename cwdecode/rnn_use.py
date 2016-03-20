#!/usr/bin/env python
#-*- coding: utf-8 -*-

import sys
import wave
import theano
import cPickle
import numpy
from config import *
import theano.tensor as T
import pyaudio
import extensions

import blocks as bl
import blocks.bricks as br
import blocks.graph as blgraph
import blocks.bricks.cost as brcost
import blocks.initialization as blinit
import blocks.bricks.recurrent as brrec
import blocks.extensions.monitoring as lbmon
import blocks.extensions as blext
import blocks.algorithms as blalg
import blocks.extensions.monitoring as blmon
import blocks.main_loop as blml

from fuel.streams import DataStream
from fuel.datasets import IterableDataset

from blocks.filter import VariableFilter
from blocks.roles import PARAMETER

from collections import OrderedDict

N_CLASSES  = len(MORSE_CHR)

x = T.ftensor3('x')

input_layer = br.MLP(
    activations=[br.Rectifier()] * 2,
    dims=[CHUNK, 64, 64],
    name='input_layer',
    weights_init=blinit.Orthogonal(0.9),
    biases_init=blinit.Constant(0.0)
)
input_layer_app = input_layer.apply(x)
input_layer.initialize()

recurrent_layer = brrec.SimpleRecurrent(
    dim=64,
    activation=br.Rectifier(),
    name='recurrent_layer',
    weights_init=blinit.Orthogonal(0.01),
    biases_init=blinit.Constant(0.0)
)
state = T.fmatrix('state')
recurrent_layer_app = recurrent_layer.apply(input_layer_app, state, iterate=False)
recurrent_layer.initialize()

output_layer = br.MLP(
    activations=[br.Rectifier()] * 1 + [None],
    dims=[64, 64, N_CLASSES],
    name='output_layer',
    weights_init=blinit.Orthogonal(0.9),
    biases_init=blinit.Constant(0.0)
)
output_layer_app = output_layer.apply(recurrent_layer_app)
output_layer.initialize()

prediction = T.argmax(br.Softmax().apply(output_layer_app.reshape((output_layer_app.shape[0]*output_layer_app.shape[1], output_layer_app.shape[2]))))

# Load net parameters
savefname = "saved_params/rnn.pickle"
with open(savefname, "r") as f:
    values = cPickle.load(f)

parameters = extensions.get_parameters([input_layer, recurrent_layer, output_layer])

for parameter_name in values:
    parameters[parameter_name].set_value(values[parameter_name])

f = theano.function([x, state], [prediction, recurrent_layer_app])

p = pyaudio.PyAudio()

stream = p.open(
    format = pyaudio.paFloat32,
    channels = 1,
    rate = FRAMERATE,
    input = True,
    output = False,
    frames_per_buffer = CHUNK
)

next_state = numpy.zeros((1, 1,64), numpy.float32)
while True:
    chunk = numpy.fromstring(stream.read(CHUNK), dtype=numpy.float32)*50
    #print max(chunk), min(chunk)
    prediction, next_state = f(numpy.array([[chunk]], dtype=numpy.float32), next_state[0])
    if prediction == 0:
        continue
    c = MORSE_CHR[prediction]
    print c
