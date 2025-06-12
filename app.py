
from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
from pymongo import MongoClient
from bson.regex import Regex
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from datetime import datetime
import cohere
import re

app = Flask(__name__)
CORS(app)

from flask import render_template
@app.route("/")
def home():
    return render_template("index.html")

co = cohere.Client("aETls8igPmzPY9xfiowlOdTKzdxcD86Faunjbdts")

# MongoDB connection
client = MongoClient("mongodb+srv://admin:FpybIN95mvvtJbVr@spiritsbox.hp9nflo.mongodb.net/spiritsbox?retryWrites=true&w=majority")
db = client["SpiritsBox"]
customers_col = db["customers"]
drinks_col = db["drinks"]
history_col = db["recommendation_history"]

def build_profile_vector(prefix, items):
    return " ".join([f"{prefix}_{item}" for item in items])

customer_bp = Blueprint("customers", __name__)

@customer_bp.route("/api/customers", methods=["GET"])
def get_customers():
    clientes = list(customers_col.find({}, {"_id": 0}))
    return jsonify(clientes)

@customer_bp.route("/api/customers/<name>", methods=["GET"])
def get_customer_detail(name):
    cliente = customers_col.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}}, {"_id": 0})
    if not cliente:
        return jsonify({"error": "Cliente no encontrado"}), 404
    return jsonify(cliente)

@customer_bp.route("/api/customers/<name>/update", methods=["POST"])
def update_customer(name):
    data = request.get_json()
    preferencias = data.get("preferences", {})
    result = customers_col.update_one(
        {"name": {"$regex": f"^{name}$", "$options": "i"}},
        {"$set": {"preferences": preferencias}}
    )
    if result.matched_count:
        return jsonify({"success": True})
    return jsonify({"error": "No se encontró el cliente"}), 404

@app.route("/clientes")
def clientes_page():
    return render_template("clientes.html")

@app.route("/recommendations_llm", methods=["POST"])
def recommendations_llm():
    data = request.get_json()
    messages = data.get("messages", [])

    # Detección del nombre desde los mensajes del usuario
    nombre = None
    patrones_nombre = [
        r"soy ([a-zA-ZÀ-ÿ\s]+)",
        r"me llamo ([a-zA-ZÀ-ÿ\s]+)",
        r"mi nombre es ([a-zA-ZÀ-ÿ\s]+)"
    ]
    for msg in messages:
        if msg["role"] == "user":
            texto = msg["content"].strip()
            for patron in patrones_nombre:
                match = re.search(patron, texto, re.IGNORECASE)
                if match:
                    nombre = match.group(1).strip()
                    break
        if nombre:
            break

    # Prompt base (sin etiquetas de rol)
    prompt = (
        "You are SpiritsBot, the virtual advisor for alcoholic drinks at SpiritsBox. "
        "Your role is to interact naturally with the client and guide them to find the best recommendations. "
        "Please follow this logical flow:\n"
        "1. Ask for the client's name if not known.\n"
        "2. If name is known, check if registered.\n"
        "3. If new, ask about preferences (type, flavor, origin).\n"
        "4. If returning, list saved preferences and ask if they want to update.\n"
        "5. Based on preferences, make personalized suggestions.\n"
        "Be friendly, curious, and helpful. Don't label yourself as 'Assistant'. Don't include role tags.\n\n"
    )

    # Añadir información del cliente si fue identificado
    if nombre:
        cliente = customers_col.find_one({
            "name": { "$regex": f"^{nombre}$", "$options": "i" }
        })

        if cliente:
            prefs = cliente.get("preferences", {})
            tipos = ", ".join(prefs.get("types", [])) or "not specified"
            sabores = ", ".join(prefs.get("flavor_profiles", [])) or "not specified"
            origenes = ", ".join(prefs.get("origins", [])) or "not specified"
            prompt += (
                f"The client is {nombre}, a returning user.\n"
                f"Their preferences are:\n"
                f"- Type: {tipos}\n"
                f"- Flavor: {sabores}\n"
                f"- Origin: {origenes}\n"
                f"Ask if they want to update or receive new suggestions.\n\n"
            )
        else:
            prompt += f"The client says their name is {nombre}, but they are new. Ask them about their preferences.\n\n"
    else:
        prompt += "You don't know the client's name yet. Kindly ask them to start.\n\n"

    # Agrega la conversación previa (sin 'Assistant:' ni 'User:')
    for m in messages:
        if m["role"] != "system":
            prompt += f"{m['content']}\n"

    # Llamada al modelo Cohere
    try:
        response = co.chat(
            model="command-r",
            message=prompt,
            temperature=0.7
        )
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html", titulo="Chatbot")

@app.route("/cliente")
def cliente():
    return render_template("cliente.html", titulo="Gestión de Clientes")

@app.route("/recomendacion")
def recomendacion():
    return render_template("recomendacion.html", titulo="Módulo de Recomendaciones")

@app.route("/historial")
def historial():
    return render_template("index.html", titulo="Historial de Recomendaciones")

@app.route("/estadisticas")
def estadisticas():
    return render_template("estadisticas.html", titulo="Dashboard de Estadísticas")

@app.route("/api/estadisticas")
def api_estadisticas():
    try:
        clientes = list(customers_col.find())
        tipos = {}
        sabores = {}
        origenes = {}

        for cliente in clientes:
            prefs = cliente.get("preferences", {})
            for t in prefs.get("types", []):
                if t:
                    tipos[t] = tipos.get(t, 0) + 1
            for s in prefs.get("flavor_profiles", []):
                if s:
                    sabores[s] = sabores.get(s, 0) + 1
            for o in prefs.get("origins", []):
                if o:
                    origenes[o] = origenes.get(o, 0) + 1

        total_recomendaciones = history_col.count_documents({})
        total_clientes = len(clientes)

        return jsonify({
            "tipos": tipos,
            "sabores": sabores,
            "origenes": origenes,
            "total_recomendaciones": total_recomendaciones,
            "total_clientes": total_clientes
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/recommendations", methods=["GET"])
def get_recommendations():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "Missing 'name' parameter"}), 400

    cliente = customers_col.find_one({"name": Regex(f"^{name}$", "i")})
    if not cliente:
        return jsonify({"error": "Client not found"}), 404

    prefs = cliente.get("preferences", {})
    prefs_text = (
        build_profile_vector("type", prefs.get("types", [])) + " " +
        build_profile_vector("profile", prefs.get("flavor_profiles", [])) + " " +
        build_profile_vector("origin", prefs.get("origins", []))
    )

    bebidas = list(drinks_col.find())
    if not bebidas:
        return jsonify({"error": "No drinks found in database"}), 500

    df = pd.DataFrame(bebidas)
    df["text"] = df.apply(
        lambda row: f"type_{row.get('type', '')} " +
                    " ".join([f"profile_{p}" for p in row.get('flavor_profile', [])]) +
                    f" origin_{row.get('origin', '')}",
        axis=1
    )
    df["name"] = df["name"].fillna("Unnamed")

    vectorizer = CountVectorizer()
    vectors = vectorizer.fit_transform([prefs_text] + df["text"].tolist())
    similarity = cosine_similarity(vectors[0:1], vectors[1:]).flatten()

    df["similarity"] = similarity
    top_matches = df.sort_values(by="similarity", ascending=False).head(5)

    results = top_matches[["name", "type", "origin", "similarity"]].to_dict(orient="records")

    history_entry = {
        "customer_name": cliente["name"],
        "date": datetime.utcnow().isoformat(),
        "recommendations": results
    }
    history_col.insert_one(history_entry)

    return jsonify(results)

@app.route("/history", methods=["GET"])
def get_history():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "Missing 'name' parameter"}), 400

    history = list(history_col.find({"customer_name": Regex(f"^{name}$", "i")}).sort("date", -1))
    for entry in history:
        entry["_id"] = str(entry["_id"])
    return jsonify(history)

@app.route("/customer")
def get_customer():
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"error": "Missing 'name' parameter"}), 400
    cliente = customers_col.find_one({"name": Regex(f"^{name}$", "i")})
    if not cliente:
        return jsonify({"error": "Client not found"}), 404
    cliente["_id"] = str(cliente["_id"])
    return jsonify(cliente)

@app.route("/customer/update", methods=["POST"])
def update_customer():
    data = request.json
    name = data.get("name", "")
    prefs = data.get("preferences", {})
    result = customers_col.update_one({"name": Regex(f"^{name}$", "i")}, {"$set": {"preferences": prefs}})
    return jsonify({"success": result.modified_count > 0})

@app.route("/recommend_all", methods=["POST"])
def recommend_all():
    clientes = list(customers_col.find())
    bebidas = list(drinks_col.find())
    
    if not bebidas:
        return jsonify({"error": "No drinks found"}), 500

    df = pd.DataFrame(bebidas)
    df["text"] = df.apply(
        lambda row: f"type_{row.get('type', '')} " +
                    " ".join([f"profile_{p}" for p in row.get('flavor_profile', [])]) +
                    f" origin_{row.get('origin', '')}",
        axis=1
    )
    df["name"] = df["name"].fillna("Unnamed")

    vectorizer = CountVectorizer()
    text_corpus = df["text"].tolist()

    resultados = []

    for cliente in clientes:
        prefs = cliente.get("preferences", {})
        prefs_text = (
            build_profile_vector("type", prefs.get("types", [])) + " " +
            build_profile_vector("profile", prefs.get("flavor_profiles", [])) + " " +
            build_profile_vector("origin", prefs.get("origins", []))
        )
        if not prefs_text.strip():
            continue  # Skip cliente sin preferencias

        vectors = vectorizer.fit_transform([prefs_text] + text_corpus)
        similarity = cosine_similarity(vectors[0:1], vectors[1:]).flatten()
        df["similarity"] = similarity
        top_matches = df.sort_values(by="similarity", ascending=False).head(5)
        recs = top_matches[["name", "type", "origin", "similarity"]].to_dict(orient="records")

        history_entry = {
            "customer_name": cliente["name"],
            "date": datetime.utcnow().isoformat(),
            "recommendations": recs
        }
        history_col.insert_one(history_entry)
        resultados.append({"cliente": cliente["name"], "total": len(recs)})

    return jsonify({
        "clientes_procesados": len(resultados),
        "detalle": resultados
    })

app.register_blueprint(customer_bp)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
