import moxing

moxing.file.copy_parallel(
    "s3://ttsingsh/sun_data_processing/yue2_files",
    "/cache/yue2_files",
)
