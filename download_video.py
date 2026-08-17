import urllib.request
url = "https://github.com/intel-iot-devkit/sample-videos/raw/master/person-bicycle-car-detection.mp4"
print("Test videosu indiriliyor, lutfen bekleyin...")
urllib.request.urlretrieve(url, "sample.mp4")
print("Video indirildi: sample.mp4")
