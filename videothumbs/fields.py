from django.db.models import FileField

from videothumbs.helpers import VideoThumbnailHelper


class VideoThumbnailField(FileField):
    attr_class = VideoThumbnailHelper

    def __init__(self, verbose_name=None, name=None, width_field=None,
        height_field=None, sizes=None, auto_crop=True, default_size=None, **kwargs):

        self.verbose_name = verbose_name
        self.name = name
        self.width_field = width_field
        self.height_field = height_field
        self.sizes = sizes
        self.auto_crop = auto_crop

        if default_size:
            self.default_size = default_size

        if sizes and not default_size:
            self.default_size = sizes[0]

        super(VideoThumbnailField, self).__init__(**kwargs)
