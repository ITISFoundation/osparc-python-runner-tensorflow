import tensorflow as tf

import requests

response = requests.get("https://www.google.com")
print(response)

msg = tf.constant("Hello, TensorFlow!")
tf.print(msg)
