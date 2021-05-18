from PIL import Image, ImageOps
import os, random
import numpy as np
from progress.bar import Bar
import h5py

save_dir = 'E:/DATA/NPY/perspective-change/'

label = 'test'

if label == 'train':
    wdir_origin = ['E:\\DATA\\perspective-change\\index_0_origin\\']
    wdir_offset = ['E:\\DATA\\perspective-change\\index_0_offset\\']
else:
    wdir_origin = ['E:\\DATA\\perspective-change\\demo_origin\\']
    wdir_offset = ['E:\\DATA\\perspective-change\\demo_offset\\']

#Test Commit

starting_point = 0
cutoff = None

raw_images_origin = [a for b in [[d+x for x in os.listdir(d)] for d in wdir_origin] for a in b][starting_point:cutoff]
raw_images_offset = [a for b in [[d+x for x in os.listdir(d)] for d in wdir_offset] for a in b][starting_point:cutoff]

wkdir = os.path.dirname(os.path.realpath(__file__))

h,w = 512,512

channels = 3

#IMAGES WILL BE PROCESSED IN CHUNKS, WHICH WILL BE SAVED AND COMPRESSED AS .NPZ
chunk_length = 1000

bar = Bar('Processing',max = len(raw_images_origin))

for chunk_index,chunk in enumerate([raw_images_origin[i:i+chunk_length] for i in range(0,len(raw_images_origin),chunk_length)]):
    x_data, y_data = [],[]
    for index,raw_image in enumerate(chunk):
        bar.next()
        xy = []

        image_origin = Image.open(raw_image).resize((w,h))
        image_offset = Image.open(raw_images_origin[index]).resize((w,h))
        
        image_origin_array = np.array(image_origin)/127.5 - 1
        image_offset_array = np.array(image_offset)/127.5 - 1

        x_data.append(np.array(image_origin_array).reshape(-1,w,h,3))
        y_data.append(np.array(image_offset_array).reshape(-1,w,h,3))
    np.savez_compressed(save_dir+'/'+'perspective-'+str(label)+'-'+str(w)+'-'+str(chunk_index)+'.npz',x=np.array(x_data),y=np.array(y_data))
    print('')
    print('SAVED: ' + str(index+1))

bar.finish()