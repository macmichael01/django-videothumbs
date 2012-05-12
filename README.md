**ABOUT**

Auto generate video thumbnails on the fly.

NOTE: This is only a proof of concept at this point. And is not 
recommended for use in a production setting just yet.

**INSTALLATION**

    pip install django-videothumbs

    OR

    git clone https://github.com/macmichael01/django-base;
    cd django-base;
    sudo python setup.py install;


**USAGE**

    - Arguments:
        *upload_to* - Path where the videos and thumbnails will be stored.
            The defining path will contain 2 subfolders, thumbnails and videos.
        *sizes* - list of tuples containing width and height coordinates to
            size a video frame to.
    - Retrieval:
        - To retrieve the video URL:
            my_object.video.url
        - To retrieve thumbnails URL's just append the dimensions:
            my_object.video.url_125x125
            my_object.video.url_300x200

    from videothumbs import VideoThumbField

    class HomeVideo(models.Model):
        video = VideoThumbField(upload_to='home_videos', thumb_sizes=((80,80),))

**TODO**

- Write unit tests.
- Performance testing.
- Add video validation.
- Add better error handling.
- Remove the need to call subprocess for generating thumbnails.
- Add an admin widget to regenerate a thumbnail or generate a thumbnail at
  a specific frame.
