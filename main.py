from flask import Flask, request, jsonify, render_template
from keras.models import load_model
from keras.preprocessing import image
import pandas as pd
import numpy as np
import tensorflow as tf
import tensorflow_hub as hub


app = Flask(__name__, template_folder="client")
model = tf.keras.models.load_model(('MODEL/plant_diseases_model.h5'), custom_objects={'KerasLayer': hub.KerasLayer})
df_info = pd.read_csv("info_penyakit.csv")
unique_label = np.array([2, 1, 3, 4, 6, 7, 8, 5])
IMAGE_SIZE = 224
df_obat = pd.read_csv("info_obat.csv")



def preprocess_image(image_path, labels=None):
    # read image
    image_data = tf.io.read_file(image_path)
    # turn jpeg into numbers
    image_data = tf.image.decode_jpeg(image_data, channels=3)
    # scaling / normalize (0,255) menjadi (0,1)
    image_data = tf.image.convert_image_dtype(image_data, dtype=tf.float32)
    # resize to (224,224)
    image_data = tf.image.resize(image_data, size=[IMAGE_SIZE, IMAGE_SIZE])
    return image_data, labels


def predict_label(img_path):
    test_images = [img_path]
    test_set = tf.data.Dataset.from_tensor_slices((tf.constant(test_images)))
    test_set = test_set.map(preprocess_image)
    test_set = test_set.batch(batch_size=32)
    test_predictions = model.predict(test_set)
    return unique_label[np.argmax(test_predictions)]


def get_disease_info(disease_id):
    data_info = df_info[df_info.id == disease_id]
    disease = data_info.penyakit.values[0]
    disease_info = data_info.informasi.values[0]
    disease_treatment = data_info.treatment.values[0]
    return disease, disease_info, disease_treatment

def get_obat_info(disease_id, landArea, minPrice, maxPrice):
    message = "Pestisida yang berhasil ditemukan"
    result = df_obat.copy()
    result.butuh = result.butuh * landArea
    result.harga = result.harga * landArea
    result = result[(result.id_penyakit == disease_id) & ((result.harga >= minPrice) & (result.harga <= maxPrice))]
    if result.shape[0] == 0:
        result = df_obat.copy()
        result.butuh = result.butuh * landArea
        result.harga = result.harga * landArea
        result = result[(result.id_penyakit == disease_id)]
        message = "Pestisida dengan harga Rp "+str(minPrice)+"-"+str(maxPrice)+" kosong. Berikut list pestisida yang tersedia."
    result = result.sort_values(by=['nama_obat', 'harga'])
    return result.to_dict(orient='records'), message


@app.route("/", methods=['GET'])
def main():
    return render_template("app.html")


@app.route("/list_data", methods=['GET'])
def get_list():
    return {'name': 'irwan'}


@app.route("/leaf_analysis", methods=["POST"])
def leaf_analysis():
    landArea = int(request.form['landArea'])
    minPrice = int(request.form['minimumPrice'])
    maxPrice = int(request.form['maximumPrice'])

    leafImg = request.files['leafImage']
    img_path = "static/" + leafImg.filename
    leafImg.save(img_path)
    disease_id = predict_label(img_path)

    disease, disease_info, disease_treatment = get_disease_info(disease_id)
    list_obat, message = get_obat_info(disease_id, landArea, minPrice, maxPrice)

    response = jsonify({
        'disease_result': disease,
        'disease_info': disease_info,
        'treatment_info': disease_treatment,
        'recommendation': list_obat,
        'message': message
    })
    response.headers.add('Access-Control-Allow-Origin', '*')
    print(response)
    return response


if __name__ == '__main__':
    app.run(debug=True)