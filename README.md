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
