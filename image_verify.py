
#import Image as IMG
from PIL import Image as IMG
from os import path,remove
import sys
import glob
import warnings

def process_image(inputImage):

    warnings.simplefilter('error', IMG.DecompressionBombWarning)

    file_formats = ['.png','.gif','.jpg','.jpeg','.tiff','.bmp','.tif']

    fileName, format = path.splitext( path.basename( inputImage ) )

    if format.lower() not in file_formats or format.lower() == '':
        print 'Bad file format: ', format
        remove( inputImage )
        return None

    # test image data
    try:
        #print path.join( settings.MEDIA_ROOT, image_path[1:])
        tmpImg = IMG.open( inputImage )
        if format.lower() not in ['.jpg', '.jpeg']:
            print "format is not .jpg or .jpeg: ",inputImage
            newImg = inputImage[0:-3]+'jpg'
            print "saving as jpg: "+newImg
            tmpImg.save( newImg )
            tmpImg = IMG.close( inputImage )
            remove( inputImage )
            tmpImg = IMG.open( newImg )

    except:
        print "bad image file (on open): ",inputImage
        remove( inputImage )
        return None

    try:
        tmpImg.verify()
    except:
        print "bad image file (on verify): ",inputImage
        remove( inputImage )
        return None

    if (tmpImg.mode != 'RGB'):
        print "bad image file (not RGB): ",inputImage
        remove( inputImage )
        return None

    return None

if __name__ == '__main__':

    if len(sys.argv) != 2:
        print('Usage: python image_verify.py <base directory>')
        exit()

    image_list = glob.glob(sys.argv[1]+'/*')
    for img in image_list:
        process_image(img)
    image_list = glob.glob(sys.argv[1]+'/*')
    for img in image_list:
        process_image(img)
