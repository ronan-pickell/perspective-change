import tensorflow as tf
import os, time
import numpy as np
from progress.bar import Bar
from PIL import Image
from tensorflow.keras.utils import plot_model

from matplotlib import pyplot as plt
from IPython import display

wkdir = os.path.dirname(os.path.realpath(__file__))

checkpoint_dir = ''

epoch_count = 1000

BUFFER_SIZE = 10000
BATCH_SIZE = 1
IMG_WIDTH = 512
IMG_HEIGHT = 512

OUTPUT_CHANNELS = 3

def gpu_mem_allocate():
    print('MEM CONFIG ++++++++++++++++++++++++++++++++++')
    config = tf.compat.v1.ConfigProto()
    from tensorflow.python.keras.backend import set_session
    #config.gpu_options.per_process_gpu_memory_fraction = 0.9
    config.gpu_options.allow_growth = True
    set_session(tf.compat.v1.Session(config=config))

gpu_mem_allocate()


def downsample(filters, size, apply_batchnorm=True):
    initializer = tf.random_normal_initializer(0., 0.02)

    result = tf.keras.Sequential()
    result.add(
            tf.keras.layers.Conv2D(filters, size, strides=2, padding='same',
                                                         kernel_initializer=initializer, use_bias=False))

    if apply_batchnorm:
        result.add(tf.keras.layers.BatchNormalization())

    result.add(tf.keras.layers.LeakyReLU())

    return result

def upsample(filters, size, apply_dropout=False):
    initializer = tf.random_normal_initializer(0., 0.02)

    result = tf.keras.Sequential()
    result.add(
        tf.keras.layers.Conv2DTranspose(filters, size, strides=2,
                                                                        padding='same',
                                                                        kernel_initializer=initializer,
                                                                        use_bias=False))

    result.add(tf.keras.layers.BatchNormalization())

    if apply_dropout:
            result.add(tf.keras.layers.Dropout(0.5))

    result.add(tf.keras.layers.ReLU())

    return result

def Generator():
    inputs = tf.keras.layers.Input(shape=[IMG_WIDTH, IMG_HEIGHT, OUTPUT_CHANNELS])

    down_stack = [
        downsample(64, 4, apply_batchnorm=False),    # (bs, 128, 128, 64)
        downsample(128, 4),    # (bs, 64, 64, 128)
        downsample(256, 4),    # (bs, 32, 32, 256)
        downsample(512, 4),    # (bs, 16, 16, 512)
        downsample(512, 4),    # (bs, 8, 8, 512)
        downsample(512, 4),    # (bs, 4, 4, 512)
        downsample(512, 4),    # (bs, 2, 2, 512)
        downsample(512, 4),    # (bs, 1, 1, 512)
        downsample(512, 4),    # (bs, 1, 1, 512)
    ]

    up_stack = [
        upsample(512, 4, apply_dropout=True),    # (bs, 2, 2, 1024)
        upsample(512, 4, apply_dropout=True),    # (bs, 2, 2, 1024)
        upsample(512, 4, apply_dropout=True),    # (bs, 4, 4, 1024)
        upsample(512, 4, apply_dropout=True),    # (bs, 8, 8, 1024)
        upsample(512, 4),    # (bs, 16, 16, 1024)
        upsample(256, 4),    # (bs, 32, 32, 512)
        upsample(128, 4),    # (bs, 64, 64, 256)
        upsample(64, 4),    # (bs, 128, 128, 128)
    ]

    initializer = tf.random_normal_initializer(0., 0.02)
    last = tf.keras.layers.Conv2DTranspose(OUTPUT_CHANNELS, 4,
                                                                                 strides=2,
                                                                                 padding='same',
                                                                                 kernel_initializer=initializer,
                                                                                 activation='tanh')    # (bs, 256, 256, 3)

    x = inputs

    # Downsampling through the model
    skips = []
    for down in down_stack:
        x = down(x)
        skips.append(x)

    skips = reversed(skips[:-1])

    # Upsampling and establishing the skip connections
    for up, skip in zip(up_stack, skips):
        x = up(x)
        x = tf.keras.layers.Concatenate()([x, skip])

    x = last(x)

    return tf.keras.Model(inputs=inputs, outputs=x)

generator = Generator()

plot_model(
    generator,
    to_file='E:\\Documents\\PRGM\\NEURAL\\perspective-change\\visuals\\model_gen.png',
    show_shapes=True,
    show_layer_names=True,
    rankdir='TB',
    dpi=64
)

LAMBDA = 100

loss_object = tf.keras.losses.BinaryCrossentropy(from_logits=True)

def generator_loss(disc_generated_output, gen_output, target):
    gan_loss = loss_object(tf.ones_like(disc_generated_output), disc_generated_output)

    l1_loss = tf.reduce_mean(tf.abs(target - gen_output))

    total_gen_loss = gan_loss + (LAMBDA * l1_loss)

    return total_gen_loss, gan_loss, l1_loss

def Discriminator():
    initializer = tf.random_normal_initializer(0., 0.02)

    inp = tf.keras.layers.Input(shape=[IMG_WIDTH, IMG_HEIGHT, OUTPUT_CHANNELS], name='input_image')
    tar = tf.keras.layers.Input(shape=[IMG_WIDTH, IMG_HEIGHT, OUTPUT_CHANNELS], name='target_image')

    x = tf.keras.layers.concatenate([inp, tar])    # (bs, 256, 256, channels*2)

    down1 = downsample(64, 4, False)(x)    # (bs, 128, 128, 64)
    down2 = downsample(128, 4)(down1)    # (bs, 64, 64, 128)
    down3 = downsample(256, 4)(down2)    # (bs, 32, 32, 256)

    zero_pad1 = tf.keras.layers.ZeroPadding2D()(down3)    # (bs, 34, 34, 256)
    conv = tf.keras.layers.Conv2D(512, 4, strides=1,kernel_initializer=initializer,use_bias=False)(zero_pad1)    # (bs, 31, 31, 512)

    batchnorm1 = tf.keras.layers.BatchNormalization()(conv)

    leaky_relu = tf.keras.layers.LeakyReLU()(batchnorm1)

    zero_pad2 = tf.keras.layers.ZeroPadding2D()(leaky_relu)    # (bs, 33, 33, 512)

    last = tf.keras.layers.Conv2D(1, 4, strides=1,kernel_initializer=initializer)(zero_pad2)    # (bs, 30, 30, 1)

    return tf.keras.Model(inputs=[inp, tar], outputs=last)

discriminator = Discriminator()

plot_model(
    discriminator,
    to_file='E:\\Documents\\PRGM\\NEURAL\\perspective-change\\visuals\\model_dis.png',
    show_shapes=True,
    show_layer_names=True,
    rankdir='TB',
    dpi=64
)

def discriminator_loss(disc_real_output, disc_generated_output):
    real_loss = loss_object(tf.ones_like(disc_real_output), disc_real_output)

    generated_loss = loss_object(tf.zeros_like(disc_generated_output), disc_generated_output)

    total_disc_loss = real_loss + generated_loss

    return total_disc_loss

generator_optimizer = tf.keras.optimizers.Adam(2e-4, beta_1=0.5)
discriminator_optimizer = tf.keras.optimizers.Adam(2e-4, beta_1=0.5)


#checkpoint_prefix = os.path.join(checkpoint_dir, "ckpt")
#checkpoint = tf.train.Checkpoint(generator_optimizer=generator_optimizer,discriminator_optimizer=discriminator_optimizer,
#                               generator=generator,discriminator=discriminator)

def generate_images(model, test_input, tar, file_index, epoch):

    predictions = []
    gen_bar = Bar('Generating ',max = len(test_input))
    for t in test_input:
        gen_bar.next()
        pred = model(t, training=True)
        predictions.append(pred)
    gen_bar.finish()
    fig=plt.figure(figsize=(15, 15),dpi=150)
    fig.tight_layout()

    display_list = [[test_input[0], predictions[0], tar[0]],
                    [test_input[1], predictions[1], tar[1]],
                    [test_input[2], predictions[2], tar[2]]]
    columns,rows = 3,3
    title = ['Input Image', 'Predicted Image', 'Ground Truth']

    for i in range(columns*rows):
        img = (((np.array(display_list[int((i/columns)%rows)][int(i%columns)][0])*0.5)+0.5)*255).astype('uint8')
        fig.add_subplot(rows,columns,i+1)
        plt.title(title[int(i%columns)])
        plt.imshow(img)
        plt.axis('off')
    plt.savefig('E:\\DATA\\img_output\\perspective-change\\output_'+str(epoch)+'_'+str(file_index)+'.png')
    plt.close()

#NUMBER OF EPOCHS PER FILE
EPOCHS = 1

import datetime
log_dir="logs/"

summary_writer = tf.summary.create_file_writer(
log_dir + "fit/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))

@tf.function
def train_step(input_image, target, epoch):
    with tf.GradientTape() as gen_tape, tf.GradientTape() as disc_tape:
        gen_output = generator(input_image, training=True)

        disc_real_output = discriminator([input_image, target], training=True)
        disc_generated_output = discriminator([input_image, gen_output], training=True)

        gen_total_loss, gen_gan_loss, gen_l1_loss = generator_loss(disc_generated_output, gen_output, target)
        disc_loss = discriminator_loss(disc_real_output, disc_generated_output)

    generator_gradients = gen_tape.gradient(gen_total_loss,generator.trainable_variables)
    discriminator_gradients = disc_tape.gradient(disc_loss,discriminator.trainable_variables)

    generator_optimizer.apply_gradients(zip(generator_gradients,generator.trainable_variables))
    discriminator_optimizer.apply_gradients(zip(discriminator_gradients,discriminator.trainable_variables))

    with summary_writer.as_default():
        tf.summary.scalar('gen_total_loss', gen_total_loss, step=epoch)
        tf.summary.scalar('gen_gan_loss', gen_gan_loss, step=epoch)
        tf.summary.scalar('gen_l1_loss', gen_l1_loss, step=epoch)
        tf.summary.scalar('disc_loss', disc_loss, step=epoch)

def fit(train_ds, file_index, epochs, test_ds, epoch_number):
    for epoch in range(epochs):
        start = time.time()

        display.clear_output(wait=True)

        #for example_input, example_target in test_ds.take(1):
        #generate_images(generator, test_dataset_x, test_dataset_y, file_index, epoch_number)
        print("Epoch: ", epoch_number, " File Index: ", file_index)

        # Train
        train_bar = Bar('Training ',max = len(train_ds))
        for n, (input_image, target) in train_ds.enumerate():
            train_bar.next()
            #print(input_image.shape,target.shape)
            #stop = input('.......')
            train_step(input_image[0], target[0], epoch)
        train_bar.finish()
        print()

        # saving (checkpoint) the model every 20 epochs
        #if (epoch + 1) % 20 == 0:
            #checkpoint.save(file_prefix=checkpoint_prefix)

        
        generate_images(generator, test_dataset_x, test_dataset_y, file_index, epoch_number)

        #print('SAVING CKPT')
        #checkpoint.save(file_prefix=checkpoint_prefix)

        print ('Time taken for epoch {} is {} sec\n'.format(epoch + 1,time.time()-start))


        

d = 'E:\\DATA\\NPY\\perspective-change\\'

cutoff = None

data_files = [d+x for x in os.listdir(d)]

training_files = [x for x in data_files if ('train' in x)]


test_files = [x for x in data_files if ('test' in x)]

print('LOADING TEST DATA')
test_file = np.load(test_files[0],allow_pickle=True)
test_dataset_x = test_file['x']
test_dataset_y = test_file['y']

test_dataset = tf.data.Dataset.from_tensor_slices((test_dataset_x,test_dataset_y))#.batch(BATCH_SIZE)

'''
for epoch_number in range(epoch_count):
    for file_index,file in enumerate(training_files):

        print('A-1')
        train_file = np.load(file,allow_pickle=True)
        print('A-2')
        train_dataset_np_x = train_file['x']
        print('A-3')
        train_dataset_np_y = train_file['y'].astype('float32')
        print('A-4')
        train_dataset = tf.data.Dataset.from_tensor_slices((train_dataset_np_x,train_dataset_np_y)).batch(BATCH_SIZE)#.shuffle(BUFFER_SIZE)
        print('A-5')

        fit(train_dataset, file_index, 1, test_dataset, epoch_number)
'''

train_file = np.load(training_files[0],allow_pickle=True)
train_dataset_np_x = train_file['x']
print('A-1')
train_dataset_np_y = train_file['y'].astype('float32')
print('A-2')
train_dataset = tf.data.Dataset.from_tensor_slices((train_dataset_np_x,train_dataset_np_y)).batch(BATCH_SIZE)#.shuffle(BUFFER_SIZE)
    
for epoch_number in range(epoch_count):

    fit(train_dataset, 0, 1, test_dataset, epoch_number)
