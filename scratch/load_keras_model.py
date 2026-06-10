import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import tensorflow as tf

model_path = "app/core/models/saved_model_month.keras"
print(f"Checking if {model_path} exists...")
if not os.path.exists(model_path):
    print("Error: Model file does not exist!")
    sys.exit(1)

print("Attempting to load model using Keras...")
try:
    model = tf.keras.models.load_model(model_path)
    print("Success: Model loaded successfully!")
    print("Model Input Shape:", model.input_shape)
    print("Model Output Shape:", model.output_shape)
    model.summary()
except Exception as e:
    print("Error: Failed to load model!")
    print(e)
    sys.exit(1)
