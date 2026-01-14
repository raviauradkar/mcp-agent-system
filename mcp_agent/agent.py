"""Main MCP Agent implementation"""

import httpx
import json
import asyncio
import requests
import os
from anthropic import Anthropic
from openai import OpenAI
from typing import Optional, List, Dict, Any
import logging

from .config import AgentConfig
from .providers import LLMProvider
from .llogger import setup_logger

logger = setup_logger(__name__)


class MCPAgent:
    """Agent that connects LLMs to MCP tools"""
    
    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize MCP Agent
        
        Args:
            config: AgentConfig instance. If None, uses defaults.
        """
        self.config = config or AgentConfig()
        self.tools = []
        self.tool_registry = {}  # ← NEW: Cache tool endpoints
        self.tools_discovered = False  # ← NEW: Track discovery state
        
        logger.info(f"Initializing MCPAgent with provider: {self.config.provider}")

        # Setup provider
        if self.config.provider == LLMProvider.OLLAMA:
            self.model = self.config.model or "mistral:latest"
            logger.info(f"Using Ollama with model: {self.model}")
    
        elif self.config.provider == LLMProvider.ANTHROPIC:
            self.model = self.config.model or "claude-sonnet-4-20250514"
            self.api_key = self.config.api_key or os.getenv("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY must be set for Anthropic provider")
            self.anthropic_client = Anthropic(api_key=self.api_key)
            logger.info(f"Using Anthropic with model: {self.model}")

        elif self.config.provider == LLMProvider.OPENAI:
            self.model = self.config.model or "gpt-4o"
            self.api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY must be set for OpenAI provider")
            self.openai_client = OpenAI(api_key=self.api_key)
            logger.info(f"Using OpenAI with model: {self.model}")

        else:
            raise ValueError(f"Unknown provider: {self.config.provider}")
    
    async def discover_tools(self) -> List[Dict]:
        """
        Fetch available tools from MCP server and cache their endpoints.
        This runs once and stores both tool definitions and direct endpoints.
        """
        if self.tools_discovered:
            logger.info("Tools already discovered, using cache")
            return self.tools
            
        logger.info(f"Discovering tools from {self.config.mcp_server_url}")
        
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(
                    f"{self.config.mcp_server_url}/tools",
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                self.tools = response.json()
            
            # Build tool registry with direct endpoints
            for tool in self.tools:
                tool_name = tool.get('function', {}).get('name')
                if tool_name:
                    self.tool_registry[tool_name] = {
                        "description": tool.get('function', {}).get('description'),
                        "parameters": tool.get('function', {}).get('parameters'),
                        "direct_endpoint": tool.get('function', {}).get('direct_endpoint'),
                        "proxy_endpoint": f"{self.config.mcp_server_url}/tools/{tool_name}"
                    }
                    logger.info(f"Discovered tool: {tool_name}")
                    if self.tool_registry[tool_name]["direct_endpoint"]:
                        logger.debug(f"  Direct: {self.tool_registry[tool_name]['direct_endpoint']}")
                    logger.debug(f"  Proxy:  {self.tool_registry[tool_name]['proxy_endpoint']}")
            
            self.tools_discovered = True
            logger.info(f"Total tools discovered: {len(self.tool_registry)}")
            return self.tools
            
        except Exception as e:
            logger.error(f"Failed to discover tools: {e}")
            raise

    async def invoke_tool(
        self, 
        tool_name: str, 
        tool_input: Dict,
        use_direct: Optional[bool] = None
    ) -> Dict:
        """
        Call a tool either directly or via MCP proxy
        
        Args:
            tool_name: Name of the tool to invoke
            tool_input: Input parameters for the tool
            use_direct: If True, call tool directly. If False, use MCP proxy.
                       If None, use config default (use_direct_tool_calls)
        """
        # Ensure tools are discovered
        if not self.tools_discovered:
            await self.discover_tools()
        
        # Check if tool exists
        if tool_name not in self.tool_registry:
            raise ValueError(
                f"Unknown tool: {tool_name}. "
                f"Available tools: {list(self.tool_registry.keys())}"
            )
        
        # Determine whether to use direct or proxy endpoint
        if use_direct is None:
            use_direct = getattr(self.config, 'use_direct_tool_calls', True)
        
        # Check if tool is forced to use proxy
        force_proxy_tools = getattr(self.config, 'force_proxy_tools', [])
        if tool_name in force_proxy_tools:
            use_direct = False
            logger.debug(f"Tool {tool_name} forced to use proxy")
        
        tool_info = self.tool_registry[tool_name]
        
        # Choose endpoint
        if use_direct:
            if not tool_info["direct_endpoint"]:
                logger.warning(
                    f"Tool {tool_name} has no direct endpoint, falling back to proxy"
                )
                endpoint = tool_info["proxy_endpoint"]
                call_type = "proxy (fallback)"
            else:
                endpoint = tool_info["direct_endpoint"]
                call_type = "direct"
        else:
            endpoint = tool_info["proxy_endpoint"]
            call_type = "proxy"
        
        logger.info(f"Invoking tool: {tool_name} ({call_type})")
        logger.debug(f"Endpoint: {endpoint}")
        logger.debug(f"Tool input: {tool_input}")
        
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    endpoint,
                    json=tool_input,
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                result = response.json()
            
            logger.info(f"Tool {tool_name} executed successfully ({call_type})")
            logger.debug(f"Tool result: {result}")
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Tool execution failed for {tool_name} ({call_type}): "
                f"Status {e.response.status_code}, Response: {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name} ({call_type}): {e}")
            raise
    
    def get_available_tools(self) -> Dict[str, str]:
        """Return a dict of available tools and their descriptions"""
        return {
            name: info["description"]
            for name, info in self.tool_registry.items()
        }
    
    def _convert_tools_for_anthropic(self) -> List[Dict]:
        """Convert OpenAI format tools to Anthropic format"""
        anthropic_tools = []
        for tool in self.tools:
            func = tool.get('function', {})
            anthropic_tools.append({
                "name": func.get('name'),
                "description": func.get('description'),
                "input_schema": func.get('parameters', {})
            })
        return anthropic_tools
    
    async def _call_anthropic(self, messages: List[Dict], 
                             use_tools: bool = True, 
                             system_prompt: Optional[str] = None) -> Any:
        """Call Anthropic API"""
        kwargs = {
            "model": self.model,
            "max_tokens": self.config.max_tokens,
            "messages": messages
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        if use_tools and self.tools:
            kwargs["tools"] = self._convert_tools_for_anthropic()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: self.anthropic_client.messages.create(**kwargs)
        )
    
    async def _call_openai(
        self,
        messages: List[Dict],
        use_tools: bool = True,
        system_prompt: Optional[str] = None
    ) -> Any:
        """Call OpenAI Responses API"""
        input_messages = []

        if system_prompt:
            input_messages.append({
                "role": "system",
                "content": system_prompt
            })

        input_messages.extend(messages)

        kwargs = {
            "model": self.model,
            "input": input_messages,
            "max_output_tokens": self.config.max_tokens
        }

        if use_tools and self.tools:
            # Transform tools for OpenAI format
            openai_tools = []
            for tool in self.tools:
                openai_tool = {
                    "type": tool["type"],
                    "name": tool["function"]["name"],  # Add name at top level
                    "function": tool["function"]
                }
                openai_tools.append(openai_tool)
            
            kwargs["tools"] = openai_tools
            kwargs["tool_choice"] = "auto"

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.openai_client.responses.create(**kwargs)
        )
    
    async def _call_ollama(self, prompt: str, use_tools: bool = True) -> Dict:
        """Call Ollama with tools support"""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        
        if use_tools and self.tools:
            payload["tools"] = self.tools
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_call_ollama, payload)
    
    def _sync_call_ollama(self, payload: Dict) -> Dict:
        """Synchronous Ollama call"""
        response = requests.post(
            self.config.ollama_url, 
            json=payload,
            timeout=self.config.timeout
        )
        response.raise_for_status()
        return response.json()
    
    async def run(self, userid: str, user_message: str, verbose: bool = True) -> str:
        """
        Run the agentic loop
        
        Args:
            userid: User identifier
            user_message: The user's query
            verbose: Whether to print debug information
            
        Returns:
            The final response from the agent
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"🤖 Query: {user_message} userId {userid}")
            print(f"{'='*60}\n")
        
        # Discover tools if not already loaded
        if not self.tools:
            await self.discover_tools()

        user_message = userid + " " + user_message
        
        messages = [{"role": "user", "content": user_message}]
        
        for iteration in range(self.config.max_iterations):
            if verbose:
                print(f"🔄 Iteration {iteration + 1}/{self.config.max_iterations}")
            
            # Call LLM based on provider
            if self.config.provider == LLMProvider.ANTHROPIC:
                response = await self._call_anthropic(
                    messages, 
                    use_tools=True, 
                    system_prompt=self.config.system_prompt
                )

                logger.debug(f"Anthropic response: {response}")
                
                # Token logging
                if hasattr(response, "usage") and response.usage:
                    input_tokens = response.usage.input_tokens
                    output_tokens = response.usage.output_tokens
                    total_tokens = input_tokens + output_tokens
                    print(f"📊 Anthropic tokens | input={input_tokens}, output={output_tokens}, total={total_tokens}")

                if response.stop_reason == "tool_use":
                    tool_use_block = next(
                        (block for block in response.content if block.type == "tool_use"),
                        None
                    )
                    
                    if tool_use_block:
                        if verbose:
                            print(f"  🔧 Calling: {tool_use_block.name}")
                            print(f"     Params: {json.dumps(tool_use_block.input, indent=2)}")
                        
                        try:
                            result = await self.invoke_tool(
                                tool_use_block.name, 
                                tool_use_block.input
                            )
                            
                            if verbose:
                                print(f"  ✅ Result: {json.dumps(result, indent=2)[:200]}...")
                            
                            messages.append({
                                "role": "assistant",
                                "content": response.content
                            })
                            
                            messages.append({
                                "role": "user",
                                "content": [{
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_block.id,
                                    "content": json.dumps(result)
                                }]
                            })
                            
                            continue
                            
                        except Exception as e:
                            if verbose:
                                print(f"  ❌ Error: {str(e)}")
                            messages.append({
                                "role": "user",
                                "content": f"Tool failed: {str(e)}"
                            })
                            continue
                
                elif response.stop_reason == "end_turn":
                    text_block = next(
                        (block for block in response.content if block.type == "text"),
                        None
                    )
                    if text_block:
                        final_response = text_block.text
                        if verbose:
                            print(f"\n✅ Answer: {final_response}\n")
                        return final_response
            
            elif self.config.provider == LLMProvider.OPENAI:
                response = await self._call_openai(
                    messages,
                    use_tools=True,
                    system_prompt=self.config.system_prompt
                )
                logger.debug(f"OpenAI response: {response}")
                
                # Token logging
                if hasattr(response, "usage") and response.usage:
                    prompt_tokens = response.usage.input_tokens
                    completion_tokens = response.usage.output_tokens
                    total_tokens = response.usage.total_tokens
                    print(f"📊 OpenAI tokens | prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}")
                
                # Get output from Responses API (not choices)
                output = response.output[0]  # Changed from response.choices[0].message
                
                # Check if output is a function call (tool call)
                if hasattr(output, 'type') and output.type == 'function':
                    # output itself IS the tool call
                    tool_name = output.name
                    tool_args = output.arguments if isinstance(output.arguments, dict) else json.loads(output.arguments)                
                    if verbose:
                        print(f"  🔧 Calling: {tool_name}")
                        print(f"     Params: {json.dumps(tool_args, indent=2)}")
                    
                    try:
                        result = await self.invoke_tool(tool_name, tool_args)
                        
                        if verbose:
                            print(f"  ✅ Result: {json.dumps(result, indent=2)[:200]}...")
                        
                        # Add assistant's tool call to messages
                        messages.append({
                            "role": "assistant",
                            "content": output.content,  # Changed from message.content
                            "tool_calls": [{
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": tool_call.function.arguments
                                }
                            }]
                        })
                        
                        # Add tool result
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result)
                        })
                        
                        continue
                        
                    except Exception as e:
                        if verbose:
                            print(f"  ❌ Error: {str(e)}")
                        messages.append({
                            "role": "user",
                            "content": f"Tool failed: {str(e)}"
                        })
                        continue
                
        else:
        # No tool call - return final response
            final_response = output  # Changed from message.content
            if verbose:
                print(f"\n✅ Answer: {final_response}\n")
                return final_response
            elif self.config.provider == LLMProvider.OLLAMA:
                prompt = messages[-1]["content"]
                response = await self._call_ollama(prompt, use_tools=True)
                message = response.get('message', {})
                
                if 'tool_calls' in message and message['tool_calls']:
                    tool_call = message['tool_calls'][0]
                    tool_name = tool_call['function']['name']
                    tool_params = tool_call['function']['arguments']
                    
                    if verbose:
                        print(f"  🔧 Calling: {tool_name}")
                    
                    try:
                        result = await self.invoke_tool(tool_name, tool_params)
                        
                        final_prompt = f"""Tool '{tool_name}' returned: {json.dumps(result)}
Based on this, answer: "{user_message}"
Provide a natural language response."""
                        
                        final_response_data = await self._call_ollama(final_prompt, use_tools=False)
                        final_response = final_response_data.get('message', {}).get('content', '')
                        
                        if verbose:
                            print(f"\n✅ Answer: {final_response}\n")
                        return final_response
                        
                    except Exception as e:
                        if verbose:
                            print(f"  ❌ Error: {str(e)}")
                        return f"Tool execution failed: {str(e)}"
                else:
                    content = message.get('content', '')
                    if verbose:
                        print(f"\n✅ Answer: {content}\n")
                    return content
        
        return "Max iterations reached"