# Social and Flirting Confidence Simulator

This project is an AI-driven social interaction simulator that uses real-time emotion analysis to provide feedback on flirting and social confidence skills through the Flirting Response Score (FRS) system.

## Features

- **Real-time FRS Analysis**: WebSocket-based streaming emotion analysis using Hume AI
- **Calibration System**: Multi-step calibration for personalized baseline emotion detection
- **Session Management**: Create, track, and analyze social interaction sessions
- **Performance Metrics**: Comprehensive scoring with medals, stars, and detailed feedback
- **Multiple Scenarios**: Support for social and romantic interaction modes
- **Video Upload**: Bonus feature for offline video analysis
- **Web-based Interface**: Simple HTML frontend for easy access

## Technology Stack

- **Backend**: FastAPI (Python async web framework)
- **AI Integration**: Hume AI for emotion detection
- **Database**: SQLite for session storage
- **Real-time Communication**: WebSockets for streaming analysis
- **Data Validation**: Pydantic models
- **Frontend**: Static HTML with JavaScript

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd social-and-flirting-confidence-simulator
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file with your Hume AI API key:
```
HUME_API_KEY=your_api_key_here
```

5. Run the application:
```bash
uvicorn main:app --reload
```

6. Open your browser to `http://localhost:8000` for the web interface, or `http://localhost:8000/docs` for API documentation.

## Usage

### Basic Workflow

1. **Start Session**: Choose a mode (social/romantic) and scenario
2. **Calibrate**: Complete calibration steps to establish emotion baseline
3. **Interact**: Engage in real-time conversation with FRS feedback
4. **End Session**: Receive final performance summary and feedback

### API Endpoints

- `POST /session/start` - Create new session
- `POST /api/calibration/start` - Begin calibration
- `WebSocket /api/ws/{session_id}` - Real-time FRS streaming
- `POST /session/end/{session_id}` - End session and get results
- `GET /feedback/{session_id}` - Retrieve session feedback

## Project Structure

See `file_description.txt` for detailed file descriptions and code flow documentation.

## Development

- Run tests: `python -m pytest`
- Format code: `black .`
- Lint code: `flake8`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
