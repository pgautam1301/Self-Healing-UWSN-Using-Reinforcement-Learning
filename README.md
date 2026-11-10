# Self-Healing Underwater Wireless Sensor Networks Using Reinforcement Learning

## Project Overview
AquaNet is a simulation and visualization platform for Self-Healing Underwater Wireless Sensor Networks (UWSN) using Reinforcement Learning.

## Main Components

### 1. AquaNet Dashboard
Interactive Streamlit dashboard featuring:
- 3D underwater network visualization
- Sensor node configuration
- Network builder
- Simulation monitoring
- Network configuration management

### 2. Underwater Simulation
- NS-3.41
- Aqua-Sim-NG
- Custom underwater network simulation
- Reinforcement Learning-based routing experiments

## Project Structure

- dashboard/ - Streamlit dashboard and 3D visualization
- simulation/ - Custom simulation code and Aqua-Sim-NG module

## Dashboard Setup

1. Install Python 3.
2. Open the dashboard directory.
3. Install dependencies:

   pip install -r requirements.txt

4. Run:

   streamlit run app.py

## Simulation Requirements

- NS-3.41
- Aqua-Sim-NG
- CMake and required build dependencies

The simulation source files are provided in the simulation directory. Configure them within a compatible NS-3.41 installation before running.

## Project Goal

To develop an intelligent underwater wireless sensor network capable of detecting failures, selecting alternate routes, and recovering communication using Reinforcement Learning.

## Contributors

Project Team - UWSN Minor Project
