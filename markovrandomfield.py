#!/usr/bin/env python2.7
# -*- coding: utf8 -*-
from __future__ import absolute_import, print_function, unicode_literals
"""defines classes that encapsulates the sci-kit learn ML algorithms"""

#general
import numpy as np
import matplotlib.pyplot as plt
import pickle
from sklearn.externals import joblib
import math
import random

#image processing
from skimage.io import imread_collection, imread, imshow, imsave
from skimage import img_as_float, img_as_uint
from scipy.ndimage.filters import gaussian_filter
import matplotlib.pyplot as plt

from skimage import measure
from scipy import ndimage as ndi

from skimage import feature


class pixelmap:
	"""
	Interface to pixelmap:

	pixelmap_a = pixelmap()	:							create a new instance of pixelmap

	pixelmap.set_conn_energy(conn_energy) :				set the strength of the connections between pixels - 
														this impact the relative importance of keeping the labels smooth vs. 
														being consistent with the superpixel-level prediction

	pixelmap.load_superpixel_classifier_predictions
	(pixel_lvl_predictions, height, width) :			load pixel level predictions from superpixel classifier, 
														need to specify height and width of image

	pixelmap.mcmc_update(temperature) :					perform 1 iteration of mcmc (iterate through every pixel), need to specify temperature

	pixelmap.mcmc_rand_update(temperature) :			perform 1 iteration of mcmc (iterate through a random sample of pixels), need to specify temperature

	pixelmap.mcmc_block_flip_update(temperature) :		perform 1 iteration of mcmc (iterate through a random sample of blocks), need to specify temperature

	pixelmap.eval_energy() :							compute the energy of the current state of pixel labels


	"""
	def __init__(self):
		self.height = None
		self.width = None
		self.pixel_labels = None #this is going to be a D dimensional array (each element is the label for 1 pixel) storing the predicted label
		self.pixel_conns = None #this is going to be a sparse DxD dimensional matrix (i,j)th element is the connection between pixel i and pixel j
		self.pixel_priors = None #this is going to be a D dimensional array (each element is the label for 1 pixel) storing the predicted probability of the pixel being road based on superpixel classifier
		self.conn_energy = None #we need to define this somewhere
		self.uncertain_pixel_list = [] # this stores the list of pixels that we are uncertain after superpixel classification; we will only run mrf on these
		self.total_energy = None #used to track the total energy of the current configuration
		#configuration fields
		self.road_threshold = 0.8
		self.nonroad_threshold = 0.2
		self.block_size = 100

	def set_conn_energy(self, conn_energy):
		self.conn_energy = conn_energy

	def load_superpixel_classifier_predictions(self, pixel_lvl_predictions, height, width):

		pixel_lvl_predictions = pixel_lvl_predictions.ravel()
		
		self.height = height
		self.width = width
		#assign labels
		self.pixel_labels = np.zeros(height*width)
			
		#Add noise
		for pixel_idx in xrange(height*width):
			if (pixel_lvl_predictions[pixel_idx] > self.road_threshold):
				self.pixel_labels[pixel_idx] = 1
			elif (pixel_lvl_predictions[pixel_idx] < self.nonroad_threshold):
				self.pixel_labels[pixel_idx] = 0

			else:
				self.uncertain_pixel_list.append(pixel_idx)
				ran_val = np.random.rand()
				if ran_val < pixel_lvl_predictions[pixel_idx]:
					self.pixel_labels[pixel_idx] = 1

		#threshold
		#self.pixel_labels[pixel_lvl_predictions>=0.4] = 1
	
		
		#load the pixel priors
		self.pixel_priors = np.maximum(np.minimum(pixel_lvl_predictions, 0.9999), 0.0001)

	def init_energy(self):
		self.total_energy = self.eval_energy()

	def pixel_index_to_posn(self, pixel_idx):
		y_pos = math.floor(pixel_idx/float(self.width))
		x_pos = pixel_idx - y_pos*self.width

		return (x_pos, y_pos)

	def pixel_posn_to_idx(self, x_pos, y_pos):
		pixel_index = y_pos*self.width+x_pos

		return pixel_index

	def neighbours_list(self, pixel_idx):
		(x_pos, y_pos) = self.pixel_index_to_posn(pixel_idx)


		neighbours_index_list = [];
		neighbours_label_list = [];

		#if the pixel is in the top row, there is no top neighbour; otherwise
		if (y_pos > 0):
			top_neighbour_idx = self.pixel_posn_to_idx(x_pos, y_pos-1)
			neighbours_index_list.append(top_neighbour_idx)
			neighbours_label_list.append(self.pixel_labels[top_neighbour_idx])

		#if the pixel is in the bottom row, there is no bottom neighbour; otherwise
		if (y_pos < self.height-1):
			bottom_neighbour_idx = self.pixel_posn_to_idx(x_pos, y_pos+1)
			neighbours_index_list.append(bottom_neighbour_idx)
			neighbours_label_list.append(self.pixel_labels[bottom_neighbour_idx])


		#if the pixel is in the left column, there is no left neighbour; otherwise
		if (x_pos > 0):
			left_neighbour_idx = self.pixel_posn_to_idx(x_pos-1, y_pos)
			neighbours_index_list.append(left_neighbour_idx)
			neighbours_label_list.append(self.pixel_labels[left_neighbour_idx])

		#if the pixel is in the right column, there is no right neighbour; otherwise
		if (x_pos < self.width-1):
			right_neighbour_idx = self.pixel_posn_to_idx(x_pos+1, y_pos)
			neighbours_index_list.append(right_neighbour_idx)
			neighbours_label_list.append(self.pixel_labels[right_neighbour_idx])

		#if the pixel is in the top row or left column, there is no top-left neighbour; otherwise
		if (y_pos > 0) and (x_pos>0):
			top_left_neighbour_idx = self.pixel_posn_to_idx(x_pos-1, y_pos-1)
			neighbours_index_list.append(top_left_neighbour_idx)
			neighbours_label_list.append(self.pixel_labels[top_left_neighbour_idx])

		#if the pixel is in the top row or right column, there is no top-right neighbour; otherwise
		if (y_pos > 0) and (x_pos < self.width-1):
			top_right_neighbour_idx = self.pixel_posn_to_idx(x_pos+1, y_pos-1)
			neighbours_index_list.append(top_right_neighbour_idx)
			neighbours_label_list.append(self.pixel_labels[top_right_neighbour_idx])

		#if the pixel is in the bottom row or left column, there is no bottom-left neighbour; otherwise
		if (y_pos < self.height-1) and (x_pos>0):
			bottom_left_neighbour_idx = self.pixel_posn_to_idx(x_pos-1, y_pos+1)
			neighbours_index_list.append(bottom_left_neighbour_idx)
			neighbours_label_list.append(self.pixel_labels[bottom_left_neighbour_idx])


		#if the pixel is in the bottom row or right column, there is no bottom-right neighbour; otherwise
		if (y_pos < self.height-1) and (x_pos < self.width-1):
			bottom_right_neighbour_idx = self.pixel_posn_to_idx(x_pos+1, y_pos+1)
			neighbours_index_list.append(bottom_right_neighbour_idx)
			neighbours_label_list.append(self.pixel_labels[bottom_right_neighbour_idx])

		return (neighbours_index_list, neighbours_label_list)

	def eval_energy(self):
		#compute the global component of energy
		global_energy = 0

		for pixel_idx in xrange(self.height*self.width):
			pixel_label = self.pixel_labels[pixel_idx]
			(neighbours_index_list, neighbours_label_list) = self.neighbours_list(pixel_idx)
			for neighbour_label in neighbours_label_list:
				global_energy += + (-1.0)*(2*pixel_label-1)*(2*neighbour_label-1)*self.conn_energy/2

		#compute individual pixel component of energy
		pixel_labels = self.pixel_labels
		pixel_priors = self.pixel_priors

		pixel_priors_t1 = 0.5*np.ones(pixel_priors.shape)
		pixel_priors_t0 = 0.5*np.ones(pixel_priors.shape)
		pixel_priors_t1[pixel_labels == 1] = pixel_priors[pixel_labels == 1]
		pixel_priors_t0[pixel_labels == 0] = pixel_priors[pixel_labels == 0]
		sum_pixel_lvl_energy = -(np.dot(pixel_labels, np.log(pixel_priors_t1)) + np.dot((1-pixel_labels), np.log(1- pixel_priors_t0)))

		total_energy = global_energy+sum_pixel_lvl_energy

		return total_energy

	def one_flip_energy_change(self, pixel_idx):
		pixel_label = self.pixel_labels[pixel_idx]
		proposed_pixel_label = 1- pixel_label
		pixel_lvl_prior = self.pixel_priors[pixel_idx]

		#compute the change in global component of energy
		old_global_energy = 0
		new_global_energy = 0
		(neighbours_index_list, neighbours_label_list) = self.neighbours_list(pixel_idx)

		#compute current energy & proposed energy
		for neighbour_label in neighbours_label_list:
			old_global_energy += (-1.0)*(2*pixel_label-1)*(2*neighbour_label-1)*self.conn_energy
			new_global_energy += (-1.0)*(2*proposed_pixel_label-1)*(2*neighbour_label-1)*self.conn_energy

		#compute change
		global_energy_change = new_global_energy - old_global_energy

		#compute the change in local component of energy
		if pixel_label == 1:
			old_local_energy = (-1)*np.log(pixel_lvl_prior)
			new_local_energy = (-1)*np.log(1-pixel_lvl_prior)
		elif pixel_label == 0:
			old_local_energy = (-1)*np.log(1-pixel_lvl_prior)
			new_local_energy = (-1)*np.log(pixel_lvl_prior)

		else:
			print('error: unexpected label value')


		#compute change
		local_energy_change = new_local_energy - old_local_energy

		#compute total change in energy
		total_energy_change = global_energy_change+local_energy_change

		return total_energy_change

	def mcmc_one_flip(self, pixel_idx, temperature):
		energy_change = self.one_flip_energy_change(pixel_idx)
		prob_flip = min(1, np.exp(-float(1/temperature)*energy_change))

		#pick a random number uniformly from 0 to 1, if the random number < prob_flip, then flip;
		#otherwise don't flip
		rand_num = np.random.rand()

		if rand_num < prob_flip:
			self.pixel_labels[pixel_idx] = 1-self.pixel_labels[pixel_idx]
			self.total_energy += energy_change


	def mcmc_update(self, temperature):
		for pixel_idx in self.uncertain_pixel_list:
			self.mcmc_one_flip(pixel_idx, temperature)

	def mcmc_rand_update(self, temperature):
		for t in xrange(5*len(self.uncertain_pixel_list)):
			pixel_idx = random.choice(self.uncertain_pixel_list)
			self.mcmc_one_flip(pixel_idx, temperature)

	def find_block(self, pixel_idx):
	#find and return block with the same pixel label
		block = [pixel_idx]
		seed_array = [pixel_idx]
		while ((len(block)<= self.block_size) and (len(seed_array)>0)):
			curr_seed = seed_array.pop(0)
			curr_seed_label = self.pixel_labels[curr_seed]
			(neighbours_index_list, neighbours_label_list) = self.neighbours_list(curr_seed)
			for neighbour_index in neighbours_index_list:
				neighbour_label = self.pixel_labels[neighbour_index]
				if ((neighbour_label == curr_seed_label) and (neighbour_index not in block)):
					block.append(neighbour_index)
					seed_array.append(neighbour_index)

		return block

	def block_flip_energy_change(self, block):
		total_energy_change = 0

		#print('size of block')
		#print(len(block))
		#print(block)

		for t in xrange(len(block)):
			#for the pixel_id in the block
			#print('t:')
			#print(t)
			pixel_idx = block[t]
			#print('pixel_idx')
			#print(pixel_idx)
			pixel_label = self.pixel_labels[pixel_idx]
			proposed_pixel_label = 1- pixel_label
			pixel_lvl_prior = self.pixel_priors[pixel_idx]

			#compute the change in global component of energy
			old_global_energy = 0
			new_global_energy = 0
			(neighbours_index_list, neighbours_label_list) = self.neighbours_list(pixel_idx)
			#print(neighbours_index_list)

			#compute current energy
			for neighbour_index in neighbours_index_list:
				if int(neighbour_index) in block:
					#print('neighbour in block')
					#print(neighbour_index)
					pass
				else:
					#print('neighbour not in block')
					#print(neighbour_index)
					neighbour_label = self.pixel_labels[neighbour_index]
					old_global_energy += (-1.0)*(2*pixel_label-1)*(2*neighbour_label-1)*self.conn_energy
					new_global_energy += (-1.0)*(2*proposed_pixel_label-1)*(2*neighbour_label-1)*self.conn_energy

			#compute change
			global_energy_change = new_global_energy - old_global_energy

			old_local_energy = 0
			new_local_energy = 0

			#compute the change in local component of energy
			if pixel_label == 1:
				old_local_energy = (-1)*np.log(pixel_lvl_prior)
				new_local_energy = (-1)*np.log(1-pixel_lvl_prior)
			elif pixel_label == 0:
				old_local_energy = (-1)*np.log(1-pixel_lvl_prior)
				new_local_energy = (-1)*np.log(pixel_lvl_prior)


			#compute change
			local_energy_change = new_local_energy - old_local_energy

			#compute total change in energy
			total_energy_change +=global_energy_change+local_energy_change

		return total_energy_change

	def find_boundary_pixel(self, seed_pixel_idx):
		seed_pixel_label = self.pixel_labels[seed_pixel_idx]
		counter = 0
		seed_array = [seed_pixel_idx]
		while ((counter <= 25) and (len(seed_array)>0)):
			counter = counter+1
			curr_seed = seed_array.pop(0)
			curr_seed_label = self.pixel_labels[curr_seed]
			if curr_seed_label != seed_pixel_label:
				return curr_seed
			else:
				(neighbours_index_list, neighbours_label_list) = self.neighbours_list(curr_seed)
				for neighbour_index in neighbours_index_list:
					seed_array.append(neighbour_index)
		return None


	def mcmc_one_block_flip(self, pixel_idx, temperature):
		boundary_pixel_idx = self.find_boundary_pixel(pixel_idx)
		if (boundary_pixel_idx != None):
			block = self.find_block(boundary_pixel_idx)
			energy_change = self.block_flip_energy_change(block)
			prob_flip = min(1, np.exp(-float(1/temperature)*energy_change))

			#pick a random number uniformly from 0 to 1, if the random number < prob_flip, then flip;
			#otherwise don't flip
			rand_num = np.random.rand()

			if rand_num < prob_flip:
				old_pixel_labels = self.pixel_labels[block]
				self.pixel_labels[block] = 1-self.pixel_labels[block]
				assert(np.all(np.logical_xor(self.pixel_labels[block]==1, old_pixel_labels==1)))
				self.total_energy += energy_change

				#print(predicted_labels.eval_energy())
				#print(predicted_labels.total_energy)


	def mcmc_block_flip_update(self, temperature):
		for t in xrange(2*len(self.uncertain_pixel_list)):
			pixel_idx = random.choice(self.uncertain_pixel_list)
			self.mcmc_one_block_flip(pixel_idx, temperature)




print('==============================')
print('Testing')
print('==============================')

print('==============================')
print('Load prediction image')
print('==============================')

image_type = np.uint16
max_val = np.iinfo(image_type).max
orig_photo = imread('example-predictions/original-photo/um_000042.png')
prediction_image = imread('example-predictions/encoded/um_road_000042-4.png', as_grey=True).astype(image_type)
image_height, image_width = prediction_image.shape[0], prediction_image.shape[1]
image_pixel_priors = prediction_image/(float(max_val))

print('========================================')
print('Apply pre-processing to prediction image')
print('=========================================')

print('Gaussian Blur')
image_pixel_priors = gaussian_filter(image_pixel_priors, 5)

# print('Bilateral Filter')
# image_pixel_priors = denoise_bilateral(image_pixel_priors, sigma_range=0.05, sigma_spatial=15)

image_pixel_priors_flat = image_pixel_priors.ravel()

#
print('Testing - Max and Min Value')
print(np.max(image_pixel_priors_flat))
print(np.min(image_pixel_priors_flat))

predicted_labels = pixelmap()

#===================================
#script for initiating the MRF class
#===================================

print('============================')
print('Initializing MRF:')
print('============================')

predicted_labels.load_superpixel_classifier_predictions(image_pixel_priors_flat, prediction_image.shape[0], prediction_image.shape[1])
predicted_labels.set_conn_energy(0.5) #this is required to set the strength of connections ()
predicted_labels.init_energy()


print('============================')
print('Image Processing Scripts:')
print('============================')

updated_predictions = np.reshape(predicted_labels.pixel_labels, [prediction_image.shape[0], prediction_image.shape[1]])

imsave('testing-orig-predictions.png', prediction_image)

imsave('testing-gaussian-filtered-predictions.png', image_pixel_priors)

imsave('testing-updated-predictions-start.png', updated_predictions)



# print('Done')
print('Size of uncertain region')
print(len(predicted_labels.uncertain_pixel_list))


print('Initial energy:')
#print(predicted_labels.eval_energy())
print(predicted_labels.total_energy)

print('MCMC update 1')
predicted_labels.mcmc_rand_update(1)
joblib.dump(predicted_labels, ('mrf_labels.pkl'))
print('...')
predicted_labels.mcmc_block_flip_update(1)
joblib.dump(predicted_labels, ('mrf_labels.pkl'))
print('...')
predicted_labels.mcmc_rand_update(1)
joblib.dump(predicted_labels, ('mrf_labels.pkl'))
print('...')
predicted_labels.mcmc_update(1)
joblib.dump(predicted_labels, ('mrf_labels.pkl'))
print(predicted_labels.eval_energy())
print(predicted_labels.total_energy)

# # print('MCMC update 2')
# # predicted_labels.mcmc_rand_update(0.02)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_block_flip_update(0.02)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_rand_update(0.02)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_update(0.02)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.eval_energy())
# # print(predicted_labels.total_energy)


# # print('MCMC update 2')
# # predicted_labels.mcmc_rand_update(0.05)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_block_flip_update(0.05)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_rand_update(0.05)
# ## joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_update(0.05)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.eval_energy())
# # print(predicted_labels.total_energy)


# # print('MCMC update 3')
# # predicted_labels.mcmc_rand_update(0.07)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_block_flip_update(0.07)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_rand_update(0.07)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_update(0.07)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.eval_energy())
# # print(predicted_labels.total_energy)


# print('============================')
# print('Run MRF')
# print('============================')

# # print('MCMC update 4')
# # predicted_labels.mcmc_rand_update(0.1)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_block_flip_update(0.1)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_rand_update(0.1)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_update(0.1)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # #print(predicted_labels.eval_energy())
# # print(predicted_labels.total_energy)

# # print('MCMC update 5')
# # predicted_labels.mcmc_rand_update(0.2)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_block_flip_update(0.2)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_rand_update(0.2)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_update(0.2)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # #print(predicted_labels.eval_energy())
# # print(predicted_labels.total_energy)

# # print('MCMC update 6')
# # predicted_labels.mcmc_rand_update(0.5)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.total_energy)
# # print('...')
# # predicted_labels.mcmc_block_flip_update(0.5)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.total_energy)
# # print('...')
# # predicted_labels.mcmc_rand_update(0.5)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.total_energy)
# # print('...')
# # predicted_labels.mcmc_block_flip_update(0.5)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.total_energy)
# # print('...')
# # predicted_labels.mcmc_rand_update(0.5)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.total_energy)
# # print('...')
# # predicted_labels.mcmc_block_flip_update(0.5)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.total_energy)
# # print('...')
# # predicted_labels.mcmc_rand_update(0.5)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.total_energy)
# # print('...')
# # predicted_labels.mcmc_block_flip_update(0.5)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.total_energy)
# # print('...')
# # predicted_labels.mcmc_rand_update(0.5)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.total_energy)
# # print('...')
# # predicted_labels.mcmc_update(0.5)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # #print(predicted_labels.eval_energy())
# # print(predicted_labels.total_energy)

# # print('MCMC update 7')
# # predicted_labels.mcmc_rand_update(0.7)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.total_energy)
# # print('...')
# # predicted_labels.mcmc_block_flip_update(0.7)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.total_energy)
# # print('...')
# # predicted_labels.mcmc_rand_update(0.7)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.total_energy)
# # print('...')
# # predicted_labels.mcmc_update(0.7)
# # predicted_labels.mcmc_block_flip_update(0.7)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.total_energy)
# # print('...')
# # predicted_labels.mcmc_rand_update(0.7)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.total_energy)
# # print('...')
# # predicted_labels.mcmc_update(0.7)
# # predicted_labels.mcmc_block_flip_update(0.7)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.total_energy)
# # print('...')
# # predicted_labels.mcmc_rand_update(0.7)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print(predicted_labels.total_energy)
# # print('...')
# # predicted_labels.mcmc_update(0.7)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # #print(predicted_labels.eval_energy())
# # print(predicted_labels.total_energy)

# # print('MCMC update 8')
# # predicted_labels.mcmc_rand_update(1)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_block_flip_update(1)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_rand_update(1)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # print('...')
# # predicted_labels.mcmc_update(1)
# # joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# # #print(predicted_labels.eval_energy())
# # print(predicted_labels.total_energy)

# print('MCMC update 9')
# predicted_labels.mcmc_rand_update(2)
# joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# print('...')
# predicted_labels.mcmc_block_flip_update(2)
# joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# print('...')
# predicted_labels.mcmc_rand_update(2)
# joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# print('...')
# predicted_labels.mcmc_update(2)
# joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# #print(predicted_labels.eval_energy())
# print(predicted_labels.total_energy)

# print('MCMC update 10')
# predicted_labels.mcmc_rand_update(4)
# joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# print('...')
# predicted_labels.mcmc_block_flip_update(4)
# joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# print('...')
# predicted_labels.mcmc_rand_update(4)
# joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# print('...')
# predicted_labels.mcmc_update(4)
# joblib.dump(predicted_labels, ('mrf_labels.pkl'))
# #print(predicted_labels.eval_energy())
# print(predicted_labels.total_energy)

# # 
# updated_predictions = np.reshape(predicted_labels.pixel_labels, [prediction_image.shape[0], prediction_image.shape[1]])

# imsave('testing-updated-predictions-end.png', updated_predictions)

# print('MCMC update 4')
# predicted_labels.mcmc_rand_update(5)
# predicted_labels.mcmc_block_flip_update(5)
# predicted_labels.mcmc_block_flip_update(5)
# predicted_labels.mcmc_update(5)
# print(predicted_labels.eval_energy())

# print('MCMC update 5')
# predicted_labels.mcmc_rand_update(7)
# predicted_labels.mcmc_block_flip_update(7)
# predicted_labels.mcmc_block_flip_update(7)
# predicted_labels.mcmc_update(7)
# print(predicted_labels.eval_energy())

# print('MCMC update 6')
# predicted_labels.mcmc_rand_update(10)
# predicted_labels.mcmc_rand_update(10)
# predicted_labels.mcmc_rand_update(10)
# predicted_labels.mcmc_update(10)
# print(predicted_labels.eval_energy())


# print('MCMC update 7')
# predicted_labels.mcmc_update(20)
# predicted_labels.mcmc_update(20)
# predicted_labels.mcmc_update(20)
# predicted_labels.mcmc_update(20)
# predicted_labels.mcmc_update(20)
# predicted_labels.mcmc_update(20)
# print(predicted_labels.eval_energy())



# print('==============================')
# print('Testing')
# print('==============================')

# #build test priors
# image_type = np.uint16
# max_val = np.iinfo(image_type).max
# prediction_image = imread('example-predictions/encoded/um_road_000042.png', as_grey=True).astype(image_type)
# image_height, image_width = prediction_image.shape[0], prediction_image.shape[1]
# image_pixel_priors_flat = prediction_image.ravel()/(float(max_val))

# image_pixel_priors_flat = np.maximum(np.minimum(image_pixel_priors_flat,0.9999), 0.0001)

# predicted_labels = pixelmap()

# predicted_labels.load_superpixel_classifier_predictions(image_pixel_priors_flat, image_height, image_width)

# predicted_labels.set_conn_energy(5) #this is required to set the strength of connections ()

# print('Initial energy:')
# print(predicted_labels.eval_energy())

# print('MCMC update 1')
# predicted_labels.mcmc_update(1)
# predicted_labels.mcmc_update(1)
# print(predicted_labels.eval_energy())

# print('MCMC update 2')
# predicted_labels.mcmc_update(2)
# predicted_labels.mcmc_update(2)
# predicted_labels.mcmc_update(2)
# print(predicted_labels.eval_energy())

# print('MCMC update 3')
# predicted_labels.mcmc_update(4)
# predicted_labels.mcmc_update(4)
# predicted_labels.mcmc_update(4)
# print(predicted_labels.eval_energy())

# print('MCMC update 4')
# predicted_labels.mcmc_update(5)
# predicted_labels.mcmc_update(5)
# predicted_labels.mcmc_update(5)
# print(predicted_labels.eval_energy())

# print('MCMC update 5')
# predicted_labels.mcmc_update(7)
# predicted_labels.mcmc_update(7)
# predicted_labels.mcmc_update(7)
# print(predicted_labels.eval_energy())

# print('MCMC update 6')
# predicted_labels.mcmc_update(10)
# predicted_labels.mcmc_update(10)
# predicted_labels.mcmc_update(10)
# predicted_labels.mcmc_update(10)
# print(predicted_labels.eval_energy())

# print('MCMC update 7')
# predicted_labels.mcmc_update(15)
# predicted_labels.mcmc_update(15)
# predicted_labels.mcmc_update(15)
# predicted_labels.mcmc_update(15)
# print(predicted_labels.eval_energy())

# print('MCMC update 8')
# predicted_labels.mcmc_update(50)
# predicted_labels.mcmc_update(50)
# predicted_labels.mcmc_update(50)
# predicted_labels.mcmc_update(50)
# predicted_labels.mcmc_update(50)
# predicted_labels.mcmc_update(50)
# print(predicted_labels.eval_energy())

# new_prediction_matrix = predicted_labels.pixel_labels.reshape((image_height, image_width))
# imsave('MRF.PNG', new_prediction_matrix)

