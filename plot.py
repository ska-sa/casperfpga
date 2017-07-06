from matplotlib import pyplot as plt
import numpy as np

def interleave(data,mode):
	""" Reorganize raw data from a RAM and return channel-selectable data

	Output format:
	Row, or data[i,:]: along time axis
	Column, or data[:,i]: channel select
	"""

	if not isinstance(data,np.ndarray) or mode not in [1,2,4]:
		raise ValueError("Invalid parameter")
	if data.shape[1] != 8:
		raise ValueError("Invalid parameter")

	if mode==1:
		return data.reshape(-1,1)
	elif mode==2:
		data = data.reshape(-1,2,4)
		data = np.einsum('ijk->jik',data)
		data = data.reshape(2,-1)
		data = np.einsum('ij->ji',data)
		return data
	else: # mode==4:
		data = data.reshape(-1,4,2)
		data = np.einsum('ijk->jik',data)
		data = data.reshape(4,-1)
		data = np.einsum('ij->ji',data)
		return data

def transform(data, resolution=8, impedance=50):
	""" Receive unsigned int data and return data in dbm
	"""
	if not isinstance(data,np.ndarray) or resolution not in range(2,17):
		raise ValueError("Invalid parameter")

	stride = 2.0 / (2**(resolution)-1)
	data = data * stride - 1;				# Voltage
	data = 10 * np.log10((data ** 2) / impedance * 1000)	# dbm
	
	return data

def draw(data):
	label = ['channel'+str(i) for i in range(1,data.shape[1]+1)]
	t = range(data.shape[0])
	hplt = plt.plot(t,data)
	plt.legend(hplt,label)
	plt.xlabel('Time')
	plt.ylabel('Power (dbm)')
	plt.show()

def visualize(data, mode, resolution=8):
	data = interleave(data,mode)
	data = transform(data, resolution)
	draw(data)
