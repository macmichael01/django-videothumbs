import cStringIO, hashlib, math, os, subprocess, time

from PIL import Image, ImageOps

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models.fields.files import FieldFile


class VideoThumbnailHelper(FieldFile):

    def __init__(self, *args, **kwargs):
        super(VideoThumbnailHelper, self).__init__(*args, **kwargs)      
        self.sizes = self.field.sizes
        self.auto_crop = self.field.auto_crop

        for size in self.sizes:
            name = 'url_%sx%s' % size
            value = self.get_thumbnail_url(size)
            setattr(self, name, value)

    def _generate_thumbnail(self, video, 
        thumbnail_width, thumbnail_height, crop=True, frames=100):

        histogram_list = []
        frame_average = []

        path, full_filename = os.path.split(self.path)
        filename, extension = os.path.splitext(full_filename)

        # By default temp frame data is stored under MEDIA_ROOT/temp
        # Make sure this directory exists.
        path = "%s/temp/" % settings.MEDIA_ROOT
        if not os.path.isdir(path):
          os.mkdir(path)
          
        hashable_value = "%s%s" % (full_filename, int(time.time()))
        filehash = hashlib.md5(hashable_value).hexdigest()
        
        frame_args = {'path': path, 'filename': filehash, 'frame': '%d'}
        frame = "%(path)s%(filename)s.%(frame)s.jpg" % frame_args

        # Build the ffmpeg shell command and run it via subprocess
        cmd_args = {'frames': frames, 'video_path': video.path, 'output': frame}
        command = "ffmpeg -y -vframes %(frames)d -i %(video_path)s %(output)s"
        command = command % cmd_args
        response = subprocess.call(command, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Fail silently if ffmpeg is not installed.
        # the ffmpeg commandline tool that is.
        if response != 0:
            return

        # Loop through the generated images, open, and 
        # generate the image histogram.
        for index in range(1, frames + 1):
            frame_name = frame % index

            # If for some reason the frame does not exist, go to next frame.
            if not os.path.exists(frame_name):
                continue

            image = Image.open(frame_name)

            # Convert to RGB if necessary
            if image.mode not in ('L', 'RGB'):
                image = image.convert('RGB')

            histogram_list.append(image.histogram())

        frames = len(histogram_list)

        # Calculate the accumulated average.
        for idx in range(len(histogram_list[0])):
            average = 0.0
            accumulation = 0.0
            for idy in range(frames):
                accumulation += histogram_list[idy][idx]
                average = (float(accumulation) / frames)
            frame_average.append(average)

        minn = -1
        minRMSE = -1

        # Calculate the mean squared error
        for idx in range(frames):
            results = 0.0
            average_count = len(frame_average)

            for idy, average in enumerate(frame_average):
                error = average - float(histogram_list[idx][idy])
                results += float((error * error)) / average_count
            rmse = math.sqrt(results)

            if minn == -1 or rmse < minRMSE:
                minn = (idx + 1)
                minRMSE = rmse

        frame_path = frame % (minn)
        image = Image.open(frame_path)

        # Crop the image if auto_crop is enabled and dimensions are the same.
        if thumbnail_width == thumbnail_height and self.auto_crop:
            width, height = image.size
            min_size = min(width, height)
            new_width = (width - min_size) / 2
            new_height = (height - min_size) / 2
            params = (
                new_width, new_height, 
                width - new_width, height - new_height
            )
            image2 = image.crop(params)
            image2.load()
            image2.thumbnail((thumbnail_width, thumbnail_height),
                Image.ANTIALIAS)
        else:
            image2 = image
            image2.thumbnail((thumbnail_width, thumbnail_height),
                Image.ANTIALIAS)

        io = cStringIO.StringIO()
        image2.save(io, 'jpeg')

        # Unlink temp files.
        for idx in range(frames):
            frame_file = frame % (idx + 1)
            os.unlink(frame_file)

        return ContentFile(io.getvalue())

    def get_thumbnail_url(self, size):
        path, full_filename = os.path.split(self.url)
        filename, extension = os.path.splitext(full_filename)
        width, height = size
        path += "/thumbnail/"
        url = '%(path)s%(filename)s.%(width)sx%(height)s.%(extension)s' % {
          'path': path, 'filename': filename, 'width': width,
          'height': height, 'extension': 'jpeg'}

        return url

    def save(self, name, content, save=True):
        super(VideoThumbnailHelper, self).save(name, content, save)
        
        path, full_filename = os.path.split(self.path)
        filename, extension = os.path.splitext(full_filename)
        path += "/thumbnail/"
        
        # By default thumbnails are stored under upload_to/thumbnails/
        # Make sure this directory exists.
        if not os.path.isdir(path):
          os.mkdir(path)

        # Cycle through the sizes and generate thumbnails.
        for size in self.sizes:
            width, height = size
            url = '%(path)s%(filename)s.%(width)sx%(height)s.%(extension)s' % {
              'path': path, 'filename': filename, 'width': width,
              'height': height, 'extension': 'jpeg'}

            data = self._generate_thumbnail(content, width, height)

            # Fail silently if there is no data.
            if not data:
              return

            self.storage.save(url, data)

    def delete(self, save=True):
        super(VideoThumbnailHelper, self).delete(save)
        path, full_filename = os.path.split(self.url)
        filename, extension = os.path.splitext(full_filename)
        path += "/thumbnail/"

        # Cycle through the thumbnails to delete.
        for size in self.sizes:
            width, height = size
            url = '%(path)s%(filename)s.%(width)sx%(height)s.%(extension)s' % {
              'path': path, 'filename': filename, 'width': width,
              'height': height, 'extension': 'jpeg'}

            try:
                self.storage.delete(url)
            except:
                pass
