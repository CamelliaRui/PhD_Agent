"""
Slack MCP integration for accessing and monitoring Slack conversations
"""

import asyncio
import os
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.rtm_v2 import RTMClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SlackMCPIntegration:
    """Slack MCP integration for accessing conversations and messages"""

    def __init__(self, token: Optional[str] = None, bot_token: Optional[str] = None):
        """
        Initialize Slack MCP integration

        Args:
            token: User OAuth token for broader access
            bot_token: Bot token for limited access
        """
        self.user_token = token or os.getenv('SLACK_USER_TOKEN')
        self.bot_token = bot_token or os.getenv('SLACK_BOT_TOKEN')

        # Use bot token by default, fallback to user token
        self.active_token = self.bot_token or self.user_token

        if not self.active_token:
            logger.warning("No Slack token configured. Please set SLACK_BOT_TOKEN or SLACK_USER_TOKEN")
            self.client = None
        else:
            self.client = WebClient(token=self.active_token)

        self.workspace_info = None
        self.user_cache = {}
        self.channel_cache = {}

    async def test_connection(self) -> Dict[str, Any]:
        """Test Slack connection and get workspace info"""
        if not self.client:
            return {"error": "Slack client not initialized. Please configure token."}

        try:
            # Test authentication
            auth_response = self.client.auth_test()
            self.workspace_info = {
                'team': auth_response['team'],
                'team_id': auth_response['team_id'],
                'user': auth_response['user'],
                'user_id': auth_response['user_id'],
                'bot_id': auth_response.get('bot_id'),
                'is_bot': 'bot_id' in auth_response
            }

            return {
                'status': 'connected',
                'workspace': self.workspace_info
            }

        except SlackApiError as e:
            return {'error': f"Slack authentication failed: {e.response['error']}"}
        except Exception as e:
            return {'error': f"Connection test failed: {str(e)}"}

    async def list_channels(self, include_private: bool = False,
                           include_archived: bool = False) -> List[Dict[str, Any]]:
        """
        List all accessible channels

        Args:
            include_private: Include private channels (requires appropriate permissions)
            include_archived: Include archived channels

        Returns:
            List of channel information
        """
        if not self.client:
            return []

        channels = []

        try:
            # Get public channels
            response = self.client.conversations_list(
                exclude_archived=not include_archived,
                types="public_channel,private_channel" if include_private else "public_channel"
            )

            for channel in response['channels']:
                channel_info = {
                    'id': channel['id'],
                    'name': channel['name'],
                    'is_private': channel.get('is_private', False),
                    'is_archived': channel.get('is_archived', False),
                    'is_member': channel.get('is_member', False),
                    'num_members': channel.get('num_members', 0),
                    'purpose': channel.get('purpose', {}).get('value', ''),
                    'topic': channel.get('topic', {}).get('value', ''),
                    'created': datetime.fromtimestamp(channel['created']) if 'created' in channel else None
                }
                channels.append(channel_info)
                self.channel_cache[channel['id']] = channel_info

            return sorted(channels, key=lambda x: x['name'])

        except SlackApiError as e:
            logger.error(f"Error listing channels: {e.response['error']}")
            return []

    async def get_channel_messages(self, channel_id: str,
                                  limit: int = 100,
                                  start_time: Optional[datetime] = None,
                                  end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get messages from a specific channel

        Args:
            channel_id: Slack channel ID
            limit: Maximum number of messages to retrieve
            start_time: Start timestamp for message history
            end_time: End timestamp for message history

        Returns:
            List of messages with metadata
        """
        if not self.client:
            return []

        try:
            kwargs = {
                'channel': channel_id,
                'limit': min(limit, 1000)  # Slack API limit
            }

            if start_time:
                kwargs['oldest'] = start_time.timestamp()
            if end_time:
                kwargs['latest'] = end_time.timestamp()

            response = self.client.conversations_history(**kwargs)

            messages = []
            for msg in response['messages']:
                # Resolve user information
                user_info = await self._get_user_info(msg.get('user', 'unknown'))

                message_data = {
                    'text': msg.get('text', ''),
                    'user': user_info.get('real_name', msg.get('user', 'unknown')),
                    'user_id': msg.get('user'),
                    'timestamp': datetime.fromtimestamp(float(msg['ts'])),
                    'ts': msg['ts'],
                    'type': msg['type'],
                    'thread_ts': msg.get('thread_ts'),
                    'reply_count': msg.get('reply_count', 0),
                    'reactions': msg.get('reactions', []),
                    'attachments': msg.get('attachments', []),
                    'files': msg.get('files', [])
                }

                messages.append(message_data)

            return messages

        except SlackApiError as e:
            logger.error(f"Error getting channel messages: {e.response['error']}")
            return []

    async def search_messages(self, query: str,
                             channel: Optional[str] = None,
                             from_user: Optional[str] = None,
                             count: int = 20) -> List[Dict[str, Any]]:
        """
        Search for messages across Slack

        Args:
            query: Search query string
            channel: Limit search to specific channel
            from_user: Limit search to specific user
            count: Maximum number of results

        Returns:
            List of matching messages
        """
        if not self.client:
            return []

        try:
            # Build search query
            search_query = query
            if channel:
                search_query += f" in:{channel}"
            if from_user:
                search_query += f" from:{from_user}"

            response = self.client.search_messages(
                query=search_query,
                count=count,
                sort="timestamp",
                sort_dir="desc"
            )

            messages = []
            for match in response.get('messages', {}).get('matches', []):
                user_info = await self._get_user_info(match.get('user', 'unknown'))

                message_data = {
                    'text': match.get('text', ''),
                    'user': user_info.get('real_name', match.get('user', 'unknown')),
                    'user_id': match.get('user'),
                    'channel': match.get('channel', {}).get('name', 'unknown'),
                    'channel_id': match.get('channel', {}).get('id'),
                    'timestamp': datetime.fromtimestamp(float(match['ts'])),
                    'permalink': match.get('permalink')
                }
                messages.append(message_data)

            return messages

        except SlackApiError as e:
            logger.error(f"Error searching messages: {e.response['error']}")
            return []

    async def get_thread_messages(self, channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
        """
        Get all messages in a thread

        Args:
            channel_id: Channel containing the thread
            thread_ts: Thread timestamp

        Returns:
            List of thread messages
        """
        if not self.client:
            return []

        try:
            response = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts
            )

            messages = []
            for msg in response['messages']:
                user_info = await self._get_user_info(msg.get('user', 'unknown'))

                message_data = {
                    'text': msg.get('text', ''),
                    'user': user_info.get('real_name', msg.get('user', 'unknown')),
                    'user_id': msg.get('user'),
                    'timestamp': datetime.fromtimestamp(float(msg['ts'])),
                    'ts': msg['ts'],
                    'thread_ts': msg.get('thread_ts')
                }
                messages.append(message_data)

            return messages

        except SlackApiError as e:
            logger.error(f"Error getting thread messages: {e.response['error']}")
            return []

    async def send_message(self, channel_id: str, text: str,
                          thread_ts: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a message to a channel

        Args:
            channel_id: Target channel ID
            text: Message text
            thread_ts: Thread timestamp to reply to

        Returns:
            Response from Slack API
        """
        if not self.client:
            return {"error": "Slack client not initialized"}

        try:
            response = self.client.chat_postMessage(
                channel=channel_id,
                text=text,
                thread_ts=thread_ts
            )

            return {
                'success': True,
                'channel': response['channel'],
                'ts': response['ts'],
                'message': response.get('message', {})
            }

        except SlackApiError as e:
            return {'error': f"Failed to send message: {e.response['error']}"}

    async def get_direct_messages(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get direct messages with a specific user

        Args:
            user_id: User ID for DM conversation
            limit: Maximum number of messages

        Returns:
            List of direct messages
        """
        if not self.client:
            return []

        try:
            # Open DM channel if needed
            response = self.client.conversations_open(users=user_id)
            channel_id = response['channel']['id']

            # Get messages from DM channel
            return await self.get_channel_messages(channel_id, limit=limit)

        except SlackApiError as e:
            logger.error(f"Error getting direct messages: {e.response['error']}")
            return []

    async def monitor_channel_realtime(self, channel_id: str, callback):
        """
        Monitor a channel for real-time messages

        Args:
            channel_id: Channel to monitor
            callback: Async function to call with new messages
        """
        if not self.bot_token:
            logger.error("Real-time monitoring requires bot token")
            return

        rtm = RTMClient(token=self.bot_token)

        @rtm.on("message")
        async def handle_message(client: RTMClient, event: Dict[str, Any]):
            if event.get('channel') == channel_id:
                user_info = await self._get_user_info(event.get('user', 'unknown'))

                message_data = {
                    'text': event.get('text', ''),
                    'user': user_info.get('real_name', 'unknown'),
                    'user_id': event.get('user'),
                    'timestamp': datetime.fromtimestamp(float(event['ts'])),
                    'channel_id': event['channel']
                }

                await callback(message_data)

        rtm.start()

    async def get_user_presence(self, user_id: str) -> Dict[str, Any]:
        """
        Get user presence status

        Args:
            user_id: User ID to check

        Returns:
            User presence information
        """
        if not self.client:
            return {}

        try:
            response = self.client.users_getPresence(user=user_id)

            return {
                'presence': response['presence'],
                'online': response['online'],
                'auto_away': response.get('auto_away', False),
                'manual_away': response.get('manual_away', False),
                'last_activity': response.get('last_activity')
            }

        except SlackApiError as e:
            logger.error(f"Error getting user presence: {e.response['error']}")
            return {}

    async def _get_user_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get user information (cached)

        Args:
            user_id: Slack user ID

        Returns:
            User information
        """
        if not user_id or not self.client:
            return {}

        if user_id in self.user_cache:
            return self.user_cache[user_id]

        try:
            response = self.client.users_info(user=user_id)
            user_info = {
                'id': user_id,
                'real_name': response['user'].get('real_name', 'Unknown'),
                'display_name': response['user'].get('profile', {}).get('display_name', ''),
                'email': response['user'].get('profile', {}).get('email', ''),
                'is_bot': response['user'].get('is_bot', False)
            }
            self.user_cache[user_id] = user_info
            return user_info

        except:
            return {'id': user_id, 'real_name': 'Unknown'}

    async def extract_research_discussions(self, keywords: List[str],
                                          days_back: int = 7) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract research-related discussions based on keywords

        Args:
            keywords: List of research keywords to search for
            days_back: Number of days to search back

        Returns:
            Categorized research discussions
        """
        discussions = {
            'papers': [],
            'ideas': [],
            'questions': [],
            'resources': [],
            'meetings': []
        }

        # Define category patterns
        patterns = {
            'papers': ['paper', 'article', 'publication', 'journal', 'conference', 'arxiv'],
            'ideas': ['idea', 'hypothesis', 'proposal', 'approach', 'method'],
            'questions': ['question', 'help', 'how', 'why', 'what if', '?'],
            'resources': ['dataset', 'code', 'github', 'library', 'tool', 'resource'],
            'meetings': ['meeting', 'discussion', 'agenda', 'schedule', 'sync']
        }

        # Search for each keyword
        for keyword in keywords:
            messages = await self.search_messages(keyword, count=100)

            for msg in messages:
                # Categorize message
                msg_text_lower = msg['text'].lower()

                for category, category_patterns in patterns.items():
                    if any(pattern in msg_text_lower for pattern in category_patterns):
                        discussions[category].append(msg)
                        break

        return discussions

    async def summarize_channel_activity(self, channel_id: str,
                                        hours_back: int = 24) -> Dict[str, Any]:
        """
        Summarize recent activity in a channel

        Args:
            channel_id: Channel to summarize
            hours_back: Hours to look back

        Returns:
            Activity summary
        """
        start_time = datetime.now() - timedelta(hours=hours_back)
        messages = await self.get_channel_messages(
            channel_id,
            start_time=start_time,
            limit=200
        )

        # Analyze messages
        user_activity = {}
        thread_count = 0
        reaction_count = 0
        file_count = 0

        for msg in messages:
            # Count user activity
            user = msg['user']
            if user not in user_activity:
                user_activity[user] = 0
            user_activity[user] += 1

            # Count threads
            if msg.get('thread_ts') and msg['thread_ts'] == msg['ts']:
                thread_count += 1

            # Count reactions
            reaction_count += sum(r.get('count', 0) for r in msg.get('reactions', []))

            # Count files
            file_count += len(msg.get('files', []))

        # Get top contributors
        top_contributors = sorted(
            user_activity.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            'channel_id': channel_id,
            'period_hours': hours_back,
            'total_messages': len(messages),
            'unique_users': len(user_activity),
            'thread_count': thread_count,
            'reaction_count': reaction_count,
            'file_count': file_count,
            'top_contributors': [
                {'user': user, 'messages': count}
                for user, count in top_contributors
            ],
            'messages_per_hour': len(messages) / hours_back if hours_back > 0 else 0
        }


# Example usage and testing
async def main():
    """Test Slack MCP integration"""

    slack = SlackMCPIntegration()

    # Test connection
    connection = await slack.test_connection()
    print(f"Connection status: {json.dumps(connection, indent=2)}")

    if connection.get('status') == 'connected':
        # List channels
        channels = await slack.list_channels()
        print(f"\nFound {len(channels)} channels")

        if channels:
            # Get messages from first channel
            first_channel = channels[0]
            print(f"\nGetting messages from #{first_channel['name']}")

            messages = await slack.get_channel_messages(
                first_channel['id'],
                limit=10
            )

            for msg in messages[:3]:
                print(f"- {msg['user']}: {msg['text'][:100]}...")

        # Search for research discussions
        print("\nSearching for research discussions...")
        discussions = await slack.extract_research_discussions(
            keywords=['research', 'paper', 'experiment'],
            days_back=7
        )

        for category, msgs in discussions.items():
            if msgs:
                print(f"\n{category.capitalize()}: {len(msgs)} messages")


if __name__ == "__main__":
    asyncio.run(main())