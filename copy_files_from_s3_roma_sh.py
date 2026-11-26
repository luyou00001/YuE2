import moxing

moxing.file.copy_parallel(
    "s3://bucket-1857/z60109380/sun_data_processing/yue2_files",
    "/cache/yue2_files",
)
