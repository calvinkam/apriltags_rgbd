#!/usr/bin/env python
import sys
import cv2
import numpy as np
import bayesplane
import plane
import transformation as tf
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import math
def main(args):
	# Declare Test Variables
	# Camera Intrinsics
	fx = 529.29
	fy = 531.28
	px = 466.96
	py = 273.26
	I = np.array([fx, 0 , px, 0, fy, py, 0, 0, 1]).reshape(3,3)
	
	x_start = 544
	x_end = 557
	y_start = 207
	y_end = 224
	rgb_image = cv2.imread("../data/iros_data2/rgb_frame0000.png")
	depth_image = cv2.imread("../data/iros_data2/depth_frame0000.png", cv2.IMREAD_ANYDEPTH)
	april_tag_rgb = rgb_image[y_start:y_end, x_start:x_end]
	april_tag_depth = depth_image[y_start:y_end, x_start:x_end]
	cv2.imshow('april_tag', april_tag_rgb)
	cv2.waitKey(0)
	all_pts = []
	for i in range(x_start, x_end):
		for j in range(y_start, y_end):
			depth = depth_image[j,i] / 1000.0
			if(depth != 0):
				x = (i - px) * depth / fx
				print x
				y = (j - py) * depth / fy
				all_pts.append([x,y,depth])
	sample_cov = 0.9
	samples_depth = np.array(all_pts)
	print "Sample points from the depth sensor"
	print samples_depth[0:5, :]
	cov = np.asarray([sample_cov] * samples_depth.shape[0])
	depth_plane_est = bayesplane.fit_plane_bayes(samples_depth, cov)

	# For now hard code the test data x y values
	# Generate homogenous matrix for pose 
	x_r = 0.885966679653
	y_r = -0.0187847792584
	z_r = -0.459534989083
	w_r = 0.0594791427379
	M = tf.quaternion_matrix([w_r,x_r,y_r,z_r]) 
	x_t = 0.201772100798
	y_t = -0.139835385971
	z_t = 1.27532936921
	M[0, 3] = x_t
	M[1, 3] = y_t
	M[2, 3] = z_t
	M_d = np.delete(M, 3, 0)
	print "Extrinsics"
	print M # pose extrinsics
	origin = np.array([0,0,0,1])
	np.transpose(origin)
	C = np.dot(I, M_d)
	coord = np.dot(C, origin)
	x_coord = coord[0] / coord[2]
	y_coord = coord[1] / coord[2]
	x_samples = np.linspace(-0.1, 0.1, num = 10)
	y_samples = np.linspace(-0.1, 0.1, num = 10)
	sample_points = []
	for i in x_samples:
		for j in y_samples:
			sample_points.append([i,j,0,1])
	sample_points = np.transpose(np.array(sample_points))
	sample_points_viz = np.dot(C, sample_points)
	sample_rgb = np.transpose(np.dot(M_d, sample_points))
	# for i in range(0, 100):
	# 	x_coord = sample_points_viz[0, i] / sample_points_viz[2, i]
	# 	y_coord = sample_points_viz[1, i] / sample_points_viz[2, i]
	# 	cv2.circle(rgb_image, (int(x_coord), int(y_coord)), 5 - int(math.pow(8 * (sample_points_viz[2, i] - 1), 2)), (255, 0,0))
	cv2.imshow('april_tag', rgb_image)
	cv2.waitKey(0)
	cv2.destroyAllWindows()
	print "Sample points from the RGB sensor"
	print  sample_rgb[0:5, :]
	cov = np.asarray([0.9] * sample_rgb.shape[0])
	rgb_plane_est = bayesplane.fit_plane_bayes(sample_rgb, cov)
	
	rgb_center = sample_rgb[50,:]
	depth_center = samples_depth[50, :]
	scale = 0.01
	## Plotting for visual effects
	print "rgb_plane_est cov: "
	print rgb_plane_est.cov
	fig = plt.figure()
	ax = fig.add_subplot(111, projection='3d')
	ax.set_xlabel('X Label')
	ax.set_ylabel('Y Label')
	ax.set_zlabel('Z Label')
	# ax.scatter(sample_rgb[:, 0], sample_rgb[:, 1], sample_rgb[:, 2], c='b')
	ax.scatter(samples_depth[:, 0], samples_depth[:, 1], samples_depth[:, 2], c='g')
   	# rgbplane = rgb_plane_est.mean.plot(center=np.array(rgb_center), scale= scale, color='b', ax=ax)
	# depthplane = depth_plane_est.mean.plot(center=np.array(depth_center), scale= scale, color='g', ax=ax)
	#plt.show()

	## Kalman Update stage
	mean_rgb = rgb_plane_est.mean.vectorize()[:, np.newaxis].T
	mean_depth = depth_plane_est.mean.vectorize()[:, np.newaxis].T
	#cov_rgb = rgb_plane_est.cov
	#cov_depth = depth_plane_est.cov
	print "cov_depth: "
	print depth_plane_est.cov
	print "cov_rgb: "
	print rgb_plane_est.cov
	cov_rgb = np.eye(4)
	cov_depth = np.eye(4)
	cov_rgb_sq = np.dot(cov_rgb.T, cov_rgb)
	cov_depth_sq = np.dot(cov_depth.T, cov_depth)
	mean_fused = np.dot((np.dot(mean_rgb, cov_rgb_sq) + np.dot(mean_depth, cov_depth_sq)) , np.linalg.inv(cov_rgb_sq + cov_depth_sq))
	mean_fused = mean_fused.flatten()
	fuse_plane = plane.Plane(mean_fused[0:3], mean_fused[3])
	# fuse_plane_plot = fuse_plane.plot(center=np.array([0.26, -0.03, 1.16]), scale= scale, color='b', ax=ax)
	average_mean = (rgb_plane_est.mean.vectorize() + depth_plane_est.mean.vectorize()) / 2
	average_plane =  plane.Plane(average_mean[0:3], average_mean[3])
	# average_plane_plot = average_plane.plot(center=np.array([0.26, -0.03, 1.16]), scale= scale, color='r', ax=ax)
	print "mean_rgb: "
	print mean_rgb 
	print "mean_depth: "
	print mean_depth
	print "mean_fused: "
	print mean_fused / np.linalg.norm(mean_fused)
	print average_mean / np.linalg.norm(average_mean)


	vector_rgb = rgb_plane_est.mean.vectorize()[0:3]
	vector_depth = depth_plane_est.mean.vectorize()[0:3]
	vector_cross = np.cross(vector_rgb, vector_depth)
	vector_sin = np.linalg.norm(vector_cross)
	vector_cos = np.dot(vector_rgb, vector_depth)
	vector_skew = np.array([[0, -vector_cross[2], vector_cross[1]],
							   [vector_cross[2], 0, -vector_cross[0]],
							   [-vector_cross[1], vector_cross[0], 0]])
	vector_eye = np.eye(3)
	R = vector_eye + vector_skew + np.linalg.matrix_power(vector_skew, 2) * (1 - vector_cos) / (vector_sin * vector_sin)
	print R
	mean_rgb_rotated = rgb_plane_est.mean.vectorize()[0 : 3, np.newaxis]
	mean_rgb_rotated = np.dot(R, mean_rgb_rotated)
	mean_rgb_rotated_r = mean_rgb_rotated.flatten()
	mean_rgb_rotated_d = np.dot(mean_rgb_rotated_r, rgb_center)
	print np.append(mean_rgb_rotated_r, mean_rgb_rotated_d)
	plane_rotated = plane.Plane(mean_rgb_rotated_r, mean_rgb_rotated_d)
	# plane_rotated_plot = plane_rotated.plot(center=np.array(rgb_center), scale= scale, color='r', ax=ax)

	rotate_mat = np.eye(4)
	rotate_mat[0:3, 0:3] = R
	sub_center = np.eye(4)
	sub_center[0:3, 3] = -1*rgb_center.T
	add_center = np.eye(4)
	add_center[0:3, 3] = rgb_center.T
	post_rotate = np.dot(add_center, np.dot(rotate_mat, sub_center))
	print "post rotate"
	print post_rotate 
	M_r = np.dot(post_rotate, M)

	Mr_d = np.delete(M_r, 3, 0)
	C_r = np.dot(I, Mr_d)
	sample_points_viz_rotate = np.dot(C_r, sample_points)
	sample_rgb_rotate = np.transpose(np.dot(Mr_d, sample_points))
	# ax.scatter(sample_rgb_rotate[:, 0], sample_rgb_rotate[:, 1], sample_rgb_rotate[:, 2], c='r')
	plt.show()
	for i in range(0, 100):
		x_coord = sample_points_viz_rotate[0, i] / sample_points_viz_rotate[2, i]
		y_coord = sample_points_viz_rotate[1, i] / sample_points_viz_rotate[2, i]
		cv2.circle(rgb_image, (int(x_coord), int(y_coord)), 5 - int(math.pow(8 * (sample_points_viz_rotate[2, i] - 1), 2)), (0, 255,0))
	cv2.imshow('april_tag', rgb_image)
	cv2.waitKey(0)
	cv2.destroyAllWindows()

if __name__ == '__main__':
	main(sys.argv)