# SecureGuard AI

### AI-Powered Retail Loss Prevention & Suspicious Activity Detection

SecureGuard AI is an experimental computer-vision platform designed to explore real-time detection of potentially suspicious activity in retail environments.

The project is being developed with a particular focus on making AI-assisted loss-prevention technology more accessible to **small and independent retail stores**, where enterprise-grade systems may be difficult to deploy or afford.

> **Project status:** Active development / prototype. The system generates signals for human review and is not intended to independently determine that theft has occurred.

## Why I Built This

Large retailers can invest heavily in sophisticated loss-prevention infrastructure. Smaller retailers often have security cameras but may not have access to advanced AI systems that can help staff review potentially suspicious activity.

This project explores whether existing camera infrastructure can be combined with **Computer Vision, Edge AI, pose analysis, and AI-assisted event analysis** to create a practical and scalable retail monitoring platform.

## High-Level Architecture

```text
                           RETAIL STORE
                                │
                         Security Cameras
                                │
                           RTSP Streams
                                │
                                ▼
                    ┌───────────────────────┐
                    │     Edge Device       │
                    │                       │
                    │  • YOLO Detection     │
                    │  • Pose Estimation    │
                    │  • Face Analysis      │
                    │  • Video Processing   │
                    │  • Event Analysis     │
                    └───────────┬───────────┘
                                │
                         Incident Metadata
                                │
                                ▼
                    ┌───────────────────────┐
                    │    Central Server     │
                    │                       │
                    │  • FastAPI APIs       │
                    │  • Authentication     │
                    │  • Incident Storage   │
                    │  • Alerts             │
                    │  • Multi-Tenant Mgmt  │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │      Dashboard        │
                    │  Human Review & Ops   │
                    └───────────────────────┘
```

## Core Capabilities

- Real-time and recorded video processing
- RTSP camera stream ingestion
- Person and object detection using YOLO-based models
- Pose-based behavior analysis
- Face-analysis experimentation
- Edge-side inference for retail locations
- Central API and incident-management services
- Multi-location / multi-tenant architecture exploration
- Alerting and incident synchronization
- Web dashboard for review and administration
- Containerized and cloud-oriented deployment workflows

## Technology Stack

### AI / Computer Vision
- Python
- YOLO / Ultralytics
- OpenCV
- Pose estimation
- DeepFace experimentation
- Vision/LLM-assisted event analysis

### Backend
- FastAPI
- REST APIs
- MongoDB
- Authentication and role-based access patterns

### Edge & Infrastructure
- NVIDIA Jetson / edge-compute experimentation
- Docker
- Linux
- RTSP camera integration
- Cloud/VPS deployment patterns

### Frontend
- Web-based monitoring and incident-review interface

## Repository Structure

```text
ai-server/
├── backend/          # Application/backend services
├── central-server/   # Central management and API services
├── edge-device/      # Edge inference and camera processing
├── frontend/         # Web UI
├── deploy/           # Deployment configuration and scripts
├── docs/             # Architecture and setup documentation
└── tests/            # Project tests
```

The edge-device implementation contains the core on-premise video-processing workflow, while the central-server architecture is intended to manage clients, incidents, authentication, alerts, and synchronization across locations.

## Edge + Central Server Design

The project separates compute-intensive vision workloads from centralized application services:

**At the retail location / edge device**
- Camera access
- RTSP capture
- YOLO inference
- Pose estimation
- Face-analysis experimentation
- Local event processing

**At the central server**
- API gateway
- Authentication
- Client and user management
- Incident storage
- Alerts
- Dashboard data
- Multi-tenant management

This design allows video processing to remain close to the camera source while sending only relevant incident/event information to centralized services.

## Current Development Focus

The project is still evolving. Current areas of improvement include:

- Improving detection reliability
- Reducing false positives
- Evaluating suspicious-behavior heuristics
- Optimizing inference on edge hardware
- Improving real-time camera processing
- Strengthening deployment automation
- Improving multi-location management
- Expanding testing and observability
- Improving privacy and responsible-AI controls

## Responsible AI & Privacy

A loss-prevention system can produce incorrect detections, so this project is designed around **human review** rather than automatic accusations or enforcement.

Key principles include:

- AI-generated events should be treated as signals, not proof of theft.
- Human review should remain part of any decision-making workflow.
- Retailers should follow applicable privacy, surveillance, biometric, and data-retention laws.
- Video and biometric data should be minimized, secured, and retained only when necessary.
- Detection performance should be tested across diverse environments before real-world deployment.

## Documentation

More detailed technical documentation is available in the [`docs/`](docs/) directory, including architecture, deployment, multi-location, and developer guidance.

Useful starting points:

- [`docs/ARCHITECTURE_CLARIFICATION.md`](docs/ARCHITECTURE_CLARIFICATION.md)
- [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md)
- [`docs/MULTI_LOCATION_DEPLOYMENT.md`](docs/MULTI_LOCATION_DEPLOYMENT.md)
- [`docs/MULTI_TENANT_ARCHITECTURE.md`](docs/MULTI_TENANT_ARCHITECTURE.md)

## Running the Project

Because this repository contains multiple services and deployment paths, setup depends on whether you are running the central-server components, edge-device components, or the full development stack.

Please refer to the documentation under [`docs/`](docs/) and the component-specific README files for the current setup steps.

## Roadmap

- [ ] Improve suspicious-event classification
- [ ] Benchmark edge inference performance
- [ ] Improve incident confidence scoring
- [ ] Add clearer demo screenshots / video
- [ ] Expand automated tests
- [ ] Improve monitoring and observability
- [ ] Harden production deployment configuration
- [ ] Improve documentation for new contributors

## Portfolio Context

This is a personal engineering project built to explore practical applications of **AI/ML, Computer Vision, Edge AI, APIs, cloud infrastructure, and production-oriented system design**.

The goal is not only to experiment with models, but also to understand how an AI system can be designed, deployed, monitored, and scaled in a real retail environment.

## Author

**Deekshith Ravula**

AI/ML & Data Engineering professional focused on building practical AI systems, computer-vision applications, Generative AI solutions, and scalable backend/data platforms.

---

If you are working on Computer Vision, Edge AI, retail technology, or practical AI systems, feedback and technical suggestions are welcome.
