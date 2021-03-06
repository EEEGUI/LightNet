"""
Created on Sat Nov 18 23:12:08 2017

@author: Utku Ozbulak - github.com/utkuozbulak
"""
import os
import cv2
import numpy as np

import torch
from torch.optim import SGD
from torchvision import models

from net_viz.misc import preprocess_image, recreate_image


class CNNLayerVisualization(object):
    """
        Produces an image that minimizes the loss of a convolution
        operation for a specific layer and filter
    """
    def __init__(self, model, selected_layer, selected_filter):
        self.model = model
        self.model.eval()
        self.selected_layer = selected_layer
        self.selected_filter = selected_filter
        self.conv_output = 0

        # Generate a random image
        self.created_image = np.uint8(np.random.uniform(150, 180, (448, 896, 3)))
        # Process image and return variable
        self.processed_image = None
        # Create the folder to export images if not exists
        if not os.path.exists('../generated'):
            os.makedirs('../generated')

    def hook_layer(self):
        def hook_function(module, grad_in, grad_out):
            # Gets the conv output of the selected filter (from selected layer)
            self.conv_output = grad_out[0, self.selected_filter]

        # Hook the selected layer
        self.model[self.selected_layer].register_forward_hook(hook_function)

    def visualise_layer_with_hooks(self):
        # Hook the selected layer
        self.hook_layer()
        # Process image and return variable
        self.processed_image = preprocess_image(self.created_image)
        # Define optimizer for the image
        # Earlier layers need higher learning rates to visualize whereas later layers need less
        optimizer = SGD([self.processed_image], lr=5, weight_decay=1e-6)
        for i in range(1, 51):
            optimizer.zero_grad()
            # Assign create image to a variable to move forward in the model
            x = self.processed_image
            for index, layer in enumerate(self.model):
                # Forward pass layer by layer
                # x is not used after this point because it is only needed to trigger
                # the forward hook function
                x = layer(x)
                # Only need to forward until the selected layer is reached
                if index == self.selected_layer:
                    # (forward hook function triggered)
                    break
            # Loss function is the mean of the output of the selected layer/filter
            # We try to minimize the mean of the output of that specific filter
            loss = torch.mean(self.conv_output)
            print('Iteration:', str(i), 'Loss:', "{0:.2f}".format(loss.data.numpy()[0]))
            # Backward
            loss.backward()
            # Update image
            optimizer.step()
            # Recreate image
            self.created_image = recreate_image(self.processed_image)
            # Save image
            if i % 5 == 0:
                cv2.imwrite('../generated/layer_vis_l' + str(self.selected_layer) +
                            '_f' + str(self.selected_filter) + '_iter'+str(i)+'.jpg',
                            self.created_image)

    def visualise_layer_without_hooks(self):
        # Process image and return variable
        self.processed_image = preprocess_image(self.created_image)
        # Define optimizer for the image
        # Earlier layers need higher learning rates to visualize whereas later layers need less
        optimizer = SGD([self.processed_image], lr=5, weight_decay=1e-6)
        for i in range(1, 51):
            optimizer.zero_grad()
            # Assign create image to a variable to move forward in the model
            x = self.processed_image
            for index, layer in enumerate(self.model):
                # Forward pass layer by layer
                x = layer(x)
                if index == self.selected_layer:
                    # Only need to forward until the selected layer is reached
                    # Now, x is the output of the selected layer
                    break
            # Here, we get the specific filter from the output of the convolution operation
            # x is a tensor of shape 1x512x28x28.(For layer 17)
            # So there are 512 unique filter outputs
            # Following line selects a filter from 512 filters so self.conv_output will become
            # a tensor of shape 28x28
            self.conv_output = x[0, self.selected_filter]
            # Loss function is the mean of the output of the selected layer/filter
            # We try to minimize the mean of the output of that specific filter
            loss = torch.mean(self.conv_output)
            print('Iteration:', str(i), 'Loss:', "{0:.2f}".format(loss.data.numpy()[0]))
            # Backward
            loss.backward()
            # Update image
            optimizer.step()
            # Recreate image
            self.created_image = recreate_image(self.processed_image)
            # Save image
            if i % 5 == 0:
                cv2.imwrite('/afs/cg.cs.tu-bs.de/home/zhang/SEDPShuffleNet/net_viz/viz_outs/layer_vis_l' +
                            str(self.selected_layer) + '_f' + str(self.selected_filter) + '_iter'+str(i)+'.jpg',
                            self.created_image)


if __name__ == '__main__':
    from models.mobilenetv2plus import MobileNetV2Plus
    from scripts.utils import convert_state_dict
    from modules import InPlaceABNWrapper
    from functools import partial

    net_h, net_w = 448, 896
    cnn_layer = 17
    filter_pos = 0

    # Fully connected layer is not needed

    model = MobileNetV2Plus(n_class=19, in_size=(net_h, net_w), width_mult=1.0,
                            out_sec=256, aspp_sec=(12, 24, 36),
                            norm_act=partial(InPlaceABNWrapper, activation="leaky_relu", slope=0.1))

    pre_weight = torch.load("/zfs/zhang/TrainLog/weights/cityscapes_mobilenetv2_best_model.pkl")
    pre_weight = pre_weight["model_state"]

    model_dict = model.state_dict()

    pretrained_dict = {k[7:]: v for k, v in pre_weight.items() if k[7:] in model_dict}
    model_dict.update(pretrained_dict)
    model.load_state_dict(model_dict)

    del pre_weight
    del model_dict
    del pretrained_dict

    layer_vis = CNNLayerVisualization(model, cnn_layer, filter_pos)

    # Layer visualization with pytorch hooks
    # layer_vis.visualise_layer_with_hooks()

    # Layer visualization without pytorch hooks
    layer_vis.visualise_layer_without_hooks()
