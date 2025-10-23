import asyncio
import cv2
import numpy as np
from hume_ai.hume_ai_client import HumeStreamClient

def emotion_callback(emotions):
    """Callback to handle emotion analysis results"""
    print("🎭 Real-time Emotion Analysis:")
    for key, value in emotions.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.3f}")
        else:
            print(f"  {key}: {value}")

async def test_webcam_realtime():
    """Test Hume AI emotion analysis with real-time webcam feed"""
    try:
        # Initialize Hume client
        client = HumeStreamClient()

        # Open webcam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open webcam")
            return

        print("🎥 Starting real-time webcam emotion analysis...")
        print("Press 'q' to quit")

        frame_count = 0
        analysis_results = {}

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Could not read frame")
                break

            frame_count += 1

            # Analyze every 30th frame to avoid overwhelming the API
            if frame_count % 30 == 0:
                try:
                    # Encode frame as JPEG bytes for Hume AI
                    success, buffer = cv2.imencode('.jpg', frame)
                    if success:
                        image_bytes = buffer.tobytes()

                        # Analyze with both Hume AI and MediaPipe body analysis
                        analysis_results = await client.quick_analyze(
                            video_bytes=image_bytes,
                            body_data={'frame': frame}
                        )

                        # Print results to console
                        emotion_callback(analysis_results)

                except Exception as e:
                    print(f"Analysis error: {e}")
                    analysis_results = {
                        "emotion_state": "error",
                        "body_language_state": "error",
                        "conversation_quality": "error"
                    }

            # Display results on frame
            display_frame = frame.copy()

            # Add emotion analysis overlay
            y_offset = 30
            cv2.putText(display_frame, f"Frame: {frame_count}", (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            y_offset += 30

            if analysis_results:
                for key, value in analysis_results.items():
                    if key in ['emotion_state', 'body_language_state', 'conversation_quality']:
                        text = f"{key}: {value}"
                        cv2.putText(display_frame, text, (10, y_offset),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        y_offset += 25

                # Show key metrics if available
                metrics_to_show = ['smile', 'eye_contact', 'posture', 'gesture']
                for metric in metrics_to_show:
                    if metric in analysis_results:
                        value = analysis_results[metric]
                        if isinstance(value, float):
                            text = f"{metric}: {value:.2f}"
                            cv2.putText(display_frame, text, (10, y_offset),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                            y_offset += 20

            # Show the frame
            cv2.imshow('Hume AI Emotion Analysis', display_frame)

            # Break loop on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        await client.disconnect()
        print("Test completed and Hume client disconnected")

    except Exception as e:
        print(f"Test error: {e}")

if __name__ == "__main__":
    asyncio.run(test_webcam_realtime())
