import google.generativeai as genai

genai.configure(api_key="AIzaSyCOw6xri88klWPnvbWtl2v_IqZxtV6Hcvo")  # Reemplaza aquí si no usas dotenv

models = genai.list_models()
for model in models:
    print(model.name, "→", model.supported_generation_methods)