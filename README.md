# 🌆 Smart City Navigator

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Project_Status-Active-success)

> 🚗 A modern, interactive web app for **smart route navigation** using **OpenRouteService API** with live maps, alternative routes, and Dijkstra’s algorithm visualization — built entirely with **Streamlit**.

---

## 🧭 Overview

The **Smart City Navigator** helps users find the **best possible route** between two points with live distance and time metrics.  
It visualizes alternative routes, displays turn-by-turn instructions, and even shows **step-by-step execution of Dijkstra’s algorithm** for educational insight.

---

## ✨ Features

- 🔍 Autocomplete location search powered by OpenRouteService  
- 🚗 Supports **Car**, **Cycling**, and **Walking** modes  
- 🛣️ Displays **multiple route options** with distance and duration  
- 🗺️ **Interactive map visualization** using Folium  
- 🧮 **Dijkstra algorithm** visualization (step-by-step & final path)  
- 📥 **Download route data (GeoJSON)** for reuse or offline storage  

---

## 🧰 Tech Stack

| Category | Technology |
|-----------|-------------|
| Language | **Python 3.10+** |
| Framework | **Streamlit** |
| Mapping | **Folium**, **streamlit-folium** |
| API | **OpenRouteService** |
| Utilities | **RapidFuzz**, **Math**, **JSON**, **Typing** |

---

## ⚙️ Installation & Setup Guide

Follow the steps below to set up and run the project locally 👇

---

### 🐍 1️⃣ Install Python

Make sure you have **Python 3.10 or newer** installed.

Check version:
```bash
python --version
If Python isn’t installed, download it from:
👉 https://www.python.org/downloads/

🔹 2️⃣ Create a Virtual Environment

In your project folder:

python -m venv venv


Activate it:

Windows

venv\Scripts\activate


Mac/Linux

source venv/bin/activate

🔹 3️⃣ Install Required Dependencies

Install all libraries using the requirements.txt file:

pip install -r requirements.txt


If you don’t have the file yet, create one with the following content 👇
(You can copy this and save it as requirements.txt in your project folder)

python_version >= 3.10
streamlit==1.39.0
openrouteservice==2.3.3
folium==0.17.0
streamlit-folium==0.21.1
rapidfuzz==3.9.3
typing_extensions>=4.9.0

🔹 4️⃣ Set Up Your OpenRouteService API Key

Go to https://openrouteservice.org/dev/

Sign up and create a free API key

In your pro1.py, find this line:

API_KEY = "your_api_key_here"


Replace it with your own key:

API_KEY = "your_generated_api_key"

🔹 5️⃣ Run the Application

Once everything is set up, start the Streamlit app:

streamlit run pro1.py
