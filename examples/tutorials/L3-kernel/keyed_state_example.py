"""
Keyed State Example - User Session Tracking

This example demonstrates how to use SAGE's keyed state support to track
user sessions with automatic state persistence.

The example implements:
1. Real-time user session tracking
2. Per-user feature aggregation
3. Time window-based aggregations
4. Automatic state persistence and recovery

Usage:
    python examples/tutorials/l3-kernel/keyed_state_example.py
"""

import time

from sage.common.core.functions import MapFunction, SinkFunction, SourceFunction
from sage.kernel.api.local_environment import LocalEnvironment

# ==============================================================================
# Data Source: User Activity Events
# ==============================================================================


class UserActivitySource(SourceFunction):
    """
    Generate simulated user activity events.

    Events include user actions like login, page_view, click, purchase, etc.
    """

    def __init__(self, num_users=5, events_per_user=10, **kwargs):
        super().__init__(**kwargs)
        self.num_users = num_users
        self.events_per_user = events_per_user
        self.counter = 0
        self.total_events = num_users * events_per_user

        # Predefined user activity patterns
        self.users = [f"user_{i}" for i in range(num_users)]
        self.actions = [
            "login",
            "page_view",
            "click",
            "add_to_cart",
            "purchase",
            "logout",
        ]
        self.pages = ["/home", "/products", "/cart", "/checkout", "/account"]

    def execute(self, data=None):
        if self.counter >= self.total_events:
            return None  # Stop

        # Generate event
        user_idx = self.counter % self.num_users
        action_idx = (self.counter // self.num_users) % len(self.actions)

        event = {
            "timestamp": time.time(),
            "user_id": self.users[user_idx],
            "action": self.actions[action_idx],
            "page": self.pages[action_idx % len(self.pages)],
            "value": (action_idx + 1) * 10,  # Simulated value
            "session_id": f"session_{self.counter // (self.num_users * 3)}",
        }

        self.counter += 1
        self.logger.info(f"Generated event: {event['user_id']} - {event['action']}")
        return event


# ==============================================================================
# Key Extractor: Extract User ID as Key
# ==============================================================================


class UserIdExtractor(MapFunction):
    """
    Extract user_id from event as the partition key.

    This enables per-user state management downstream.
    """

    def execute(self, event: dict) -> str:
        user_id = event["user_id"]
        self.logger.debug(f"Extracted key: {user_id}")
        return user_id


# ==============================================================================
# Keyed State Function: User Session Manager
# ==============================================================================


class UserSessionManager(MapFunction):
    """
    Manage user sessions with keyed state.

    This function demonstrates:
    1. Accessing current key via ctx.get_key()
    2. Maintaining per-user state (automatically persisted)
    3. Aggregating metrics per user
    4. Time-based session management

    State Structure:
        self.user_sessions = {
            user_id: {
                'first_seen': timestamp,
                'last_seen': timestamp,
                'session_count': int,
                'current_session': {...},
                'total_value': float,
                'action_counts': {...}
            }
        }
    """

    def __init__(self, session_timeout=300, **kwargs):
        super().__init__(**kwargs)
        # Keyed state - automatically persisted by SAGE
        self.user_sessions = {}
        self.session_timeout = session_timeout

        # Global metrics (not keyed)
        self.total_events_processed = 0
        self.unique_users_seen = set()

    def execute(self, event: dict):
        # Get current packet's key (user_id in this case)
        user_id = self.ctx.get_key()

        # Update global metrics
        self.total_events_processed += 1
        self.unique_users_seen.add(user_id)

        # Initialize user session if first time seeing this user
        if user_id not in self.user_sessions:
            self._initialize_user_session(user_id, event)
        else:
            self._update_user_session(user_id, event)

        # Get current session state
        session = self.user_sessions[user_id]

        # Prepare enriched event with session context
        enriched_event = {
            "original_event": event,
            "user_id": user_id,
            "session_metrics": {
                "session_count": session["session_count"],
                "current_session_actions": len(session["current_session"]["actions"]),
                "total_value": session["total_value"],
                "session_duration": time.time()
                - session["current_session"]["start_time"],
                "lifetime_actions": sum(session["action_counts"].values()),
            },
            "global_metrics": {
                "total_events": self.total_events_processed,
                "unique_users": len(self.unique_users_seen),
            },
        }

        self.logger.info(
            f"User {user_id}: Session #{session['session_count']}, "
            f"Total Value: ${session['total_value']:.2f}, "
            f"Actions: {sum(session['action_counts'].values())}"
        )

        return enriched_event

    def _initialize_user_session(self, user_id: str, event: dict):
        """Initialize state for a new user"""
        current_time = time.time()

        self.user_sessions[user_id] = {
            "first_seen": current_time,
            "last_seen": current_time,
            "session_count": 1,
            "current_session": {
                "session_id": event["session_id"],
                "start_time": current_time,
                "actions": [event["action"]],
                "pages_visited": [event["page"]],
            },
            "total_value": event["value"],
            "action_counts": {event["action"]: 1},
        }

        self.logger.info(f"Initialized session for new user: {user_id}")

    def _update_user_session(self, user_id: str, event: dict):
        """Update existing user session"""
        session = self.user_sessions[user_id]
        current_time = time.time()

        # Check if we need to start a new session (timeout or explicit session change)
        time_since_last = current_time - session["last_seen"]
        session_changed = (
            event["session_id"] != session["current_session"]["session_id"]
        )

        if time_since_last > self.session_timeout or session_changed:
            # Start new session
            session["session_count"] += 1
            session["current_session"] = {
                "session_id": event["session_id"],
                "start_time": current_time,
                "actions": [event["action"]],
                "pages_visited": [event["page"]],
            }
            self.logger.info(
                f"Started new session #{session['session_count']} for user {user_id}"
            )
        else:
            # Update current session
            session["current_session"]["actions"].append(event["action"])
            if event["page"] not in session["current_session"]["pages_visited"]:
                session["current_session"]["pages_visited"].append(event["page"])

        # Update session state
        session["last_seen"] = current_time
        session["total_value"] += event["value"]

        # Update action counts
        action = event["action"]
        session["action_counts"][action] = session["action_counts"].get(action, 0) + 1


# ==============================================================================
# Window Aggregation Function
# ==============================================================================


class TimeWindowAggregator(MapFunction):
    """
    Perform time-based window aggregations with keyed state.

    Demonstrates:
    1. Sliding time windows per user
    2. Automatic cleanup of old windows
    3. Aggregations within windows
    """

    def __init__(self, window_size=60, **kwargs):  # 60 second windows
        super().__init__(**kwargs)
        self.window_size = window_size
        # Keyed state: {user_id: {window_id: [events]}}
        self.window_data = {}

    def execute(self, enriched_event: dict):
        user_id = self.ctx.get_key()
        current_time = time.time()
        window_id = int(current_time // self.window_size)

        # Initialize user's window data
        if user_id not in self.window_data:
            self.window_data[user_id] = {}

        # Add event to current window
        if window_id not in self.window_data[user_id]:
            self.window_data[user_id][window_id] = []

        self.window_data[user_id][window_id].append(enriched_event)

        # Cleanup old windows (keep last 3 windows)
        old_windows = [wid for wid in self.window_data[user_id] if wid < window_id - 2]
        for wid in old_windows:
            del self.window_data[user_id][wid]

        # Calculate window aggregations
        current_window = self.window_data[user_id][window_id]
        aggregations = {
            "window_id": window_id,
            "window_start": window_id * self.window_size,
            "window_end": (window_id + 1) * self.window_size,
            "event_count": len(current_window),
            "total_value": sum(e["original_event"]["value"] for e in current_window),
            "unique_actions": len(
                {e["original_event"]["action"] for e in current_window}
            ),
        }

        return {
            "user_id": user_id,
            "window": aggregations,
            "latest_event": enriched_event,
        }


# ==============================================================================
# Sink: Display Results
# ==============================================================================


class ResultDisplaySink(SinkFunction):
    """Display processed results with session and window information"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.result_count = 0

    def execute(self, result: dict):
        self.result_count += 1

        print(f"\n{'=' * 70}")
        print(f"Result #{self.result_count}")
        print(f"{'=' * 70}")

        # User info
        print(f"👤 User: {result['user_id']}")

        # Window info
        if "window" in result:
            window = result["window"]
            print(f"\n📊 Window Aggregation (Window ID: {window['window_id']}):")
            print(f"   Events in Window: {window['event_count']}")
            print(f"   Total Value: ${window['total_value']:.2f}")
            print(f"   Unique Actions: {window['unique_actions']}")

        # Session info
        if "latest_event" in result and "session_metrics" in result["latest_event"]:
            metrics = result["latest_event"]["session_metrics"]
            print("\n📈 Session Metrics:")
            print(f"   Session #: {metrics['session_count']}")
            print(f"   Current Session Actions: {metrics['current_session_actions']}")
            print(f"   Lifetime Value: ${metrics['total_value']:.2f}")
            print(f"   Total Actions: {metrics['lifetime_actions']}")
            print(f"   Session Duration: {metrics['session_duration']:.1f}s")

        # Global metrics
        if "latest_event" in result and "global_metrics" in result["latest_event"]:
            global_m = result["latest_event"]["global_metrics"]
            print("\n🌍 Global Metrics:")
            print(f"   Total Events Processed: {global_m['total_events']}")
            print(f"   Unique Users: {global_m['unique_users']}")

        return result


# ==============================================================================
# Main Example
# ==============================================================================


def main():
    """
    Run the keyed state example.

    Pipeline:
        UserActivitySource
        -> KeyBy(UserIdExtractor)
        -> Map(UserSessionManager)  # Maintains per-user sessions
        -> Map(TimeWindowAggregator)  # Maintains per-user time windows
        -> Sink(ResultDisplaySink)
    """
    print("\n" + "=" * 70)
    print("SAGE Keyed State Example - User Session Tracking")
    print("=" * 70)

    # Create environment
    env = LocalEnvironment("keyed_state_example")

    # Build pipeline
    (
        env.from_source(
            UserActivitySource,
            num_users=3,  # 3 users
            events_per_user=8,  # 8 events each
            delay=0.5,  # 0.5s between events
        )
        .keyby(UserIdExtractor, strategy="hash")  # Partition by user_id
        .map(UserSessionManager, session_timeout=10)  # Track sessions
        .map(TimeWindowAggregator, window_size=30)  # 30-second windows
        .sink(ResultDisplaySink)
    )

    print("\n🚀 Starting pipeline...")
    print("   - 3 users, 8 events each (24 total events)")
    print("   - Events generated every 0.5 seconds")
    print("   - Sessions tracked per user with 10s timeout")
    print("   - Time windows of 30 seconds per user")
    print()

    try:
        # Submit and run
        env.submit()

        # Let it run for a while
        time.sleep(15)

        print("\n" + "=" * 70)
        print("Pipeline completed successfully!")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        env.close()


if __name__ == "__main__":
    main()
