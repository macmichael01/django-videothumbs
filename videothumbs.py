# -*- encoding: utf-8 -*-
"""
django-videothumbs
"""

import cStringIO
import sys, os, urllib, re, math
import shutil, string, datetime, time
import Image, ImageOps
from PIL import Image

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import FileField
from django.db.models.fields.files import FieldFile


def generate_thumb(video, thumb_size, format='jpg', frames=100):
    histogram = []
    framemask = "%s%s%s%s" % (settings.FILE_UPLOAD_TEMP_DIR,
                              video.name.split('/')[-1].split('.')[0] + str(time.time()),
                              '.%d.',
                              format)
    # ffmpeg command for grabbing N number of frames
    cmd = "ffmpeg -y -vframes %d -i %s %s" % (frames, video.path, framemask)
    # make sure that this command worked or return.
    if os.system(cmd) != 0:
        raise "ffmpeg not installed"
    
    # loop through the generated images, open, and generate the image histogram.
    for i in range(1, frames + 1):
        fname = framemask % i
        
        if not os.path.exists(fname):
            break
            
        image = Image.open(fname)
            
        # Convert to RGB if necessary
        if image.mode not in ('L', 'RGB'):
            image = image.convert('RGB')
            
        # The list of image historgrams
        histogram.append(image.histogram())
        
    n = len(histogram)
    avg = []
        
    # Get the image average of the first image
    for c in range(len(histogram[0])):
        ac = 0.0
        for i in range(n):
            ac = ac + (float(histogram[i][c])/n)
        avg.append(ac)

    minn = -1
    minRMSE = -1
    
    # Compute the mean squared error  
    for i in range(1, n+1):
        results = 0.0
        num = len(avg)
        
        for j in range(num):
            median_error = avg[j] - float(histogram[i-1][j]);
            results += (median_error * median_error) / num;
        rmse = math.sqrt(results);
        
        if minn == -1 or rmse < minRMSE:
            minn = i
            minRMSE = rmse
    
    file_location = framemask % (minn)
    image = Image.open(file_location)
    thumb_w, thumb_h = thumb_size
    
    # If you want to generate a square thumbnail
    if thumb_w == thumb_h:
        # quad
        xsize, ysize = image.size
        # get minimum size
        minsize = min(xsize, ysize)
        # largest square possible in the image
        xnewsize = (xsize-minsize)/2
        ynewsize = (ysize-minsize)/2
        # crop it
        image2 = image.crop((xnewsize, ynewsize, xsize-xnewsize, ysize-ynewsize))
        # load is necessary after crop                
        image2.load()
        # thumbnail of the cropped image (with ANTIALIAS to make it look better)
        image2.thumbnail(thumb_size, Image.ANTIALIAS)
    else:
        # not quad
        image2 = image
        image2.thumbnail(thumb_size, Image.ANTIALIAS)

    io = cStringIO.StringIO()
    
    # PNG and GIF are the same, JPG is JPEG
    if format.upper()=='JPG':
        format = 'JPEG'

    image2.save(io, format)
        
    # unlink temp files
    for i in range(1, n+1):
        fname = framemask % i
        os.unlink(fname)
    return ContentFile(io.getvalue())


class VideoThumbFieldFile(FieldFile):

    def __init__(self, *args, **kwargs):
        super(VideoThumbFieldFile, self).__init__(*args, **kwargs)
        self.sizes = self.field.sizes

        if self.sizes:
            def get_size(self, size):
                if not self:
                    return ''
                else:
                    split = self.url.rsplit('.', 1)
                    thumb_url = '%s.%sx%s.%s' % (split[0], w, h, split[1])
                    return thumb_url

            for size in self.sizes:
                (w,h) = size
                setattr(self, 'url_%sx%s' % (w, h), get_size(self, size))

    def save(self, name, content, save=True):
        super(VideoThumbFieldFile, self).save(name, content, save)
        if self.sizes:
            for size in self.sizes:
                (w, h) = size
                split = name.rsplit('.',1)
                # TODO: give the user the option to pick the thumbnail format.
                thumb_name = "%s%s%s.%sx%s.%s" % (self.path.split(self.name)[0],
                                                self.field.upload_to,
                                                self.name.split('/')[-1].split('.')[0], 
                                                w, h, "jpg")
                print self.field.upload_to, dir(name), dir(content), thumb_name
                # you can use another thumbnailing function if you like
                thumb_content = generate_thumb(content, size)
                thumb_name_ = self.storage.save(thumb_name, thumb_content)        

                if not thumb_name == thumb_name_:
                    raise ValueError('There is already a file named %s' % thumb_name)

    def delete(self, save=True):
        name=self.name
        super(VideoThumbFieldFile, self).delete(save)
        if self.sizes:
            for size in self.sizes:
                (w,h) = size
                split = name.rsplit('.',1)
                thumb_name = "%s%s%s.%sx%s.%s" % (self.path.split(self.name)[0],
                                                self.field.upload_to,
                                                self.name.split('/')[-1].split('.')[0], 
                                                w, h, "jpg")
                try:
                    self.storage.delete(thumb_name)
                except:
                    pass


class VideoThumbField(FileField):
    attr_class = VideoThumbFieldFile
    """
    Usage example:
    ==============
    video = VideoThumbField(upload_to='videos', sizes=((125,125),(300,200),))

    To retrieve video URL, exactly the same way as with FileField:
        my_object.video.url
    To retrieve thumbnails URL's just add the size to it:
        my_object.video.url_125x125
        my_object.video.url_300x200

    Note: The 'sizes' attribute is not required. If you don't provide it, 
    VideoThumbField will act as a VideoField accepting only valid videos files

    How it works:
    =============
    For each size in the 'sizes' atribute of the field it generates a 
    thumbnail with that size and stores it following this format:

    filename.[width]x[height].extension

    For storing a file called "video.mpeg" it saves:
    video.mpeg          (original file)
    video.125x125.jpg  (first thumbnail)
    video.300x200.jpg  (second thumbnail)

    Note: django-videothumbs assumes that if filename "filename.jpg" is available 
    filenames with this format "filename.[widht]x[height].jpg" will be available, too.

    """
    def __init__(self, verbose_name=None, name=None, width_field=None, height_field=None, sizes=None, **kwargs):
        self.verbose_name=verbose_name
        self.name=name
        self.width_field=width_field
        self.height_field=height_field
        self.sizes = sizes
        super(VideoThumbField, self).__init__(**kwargs)