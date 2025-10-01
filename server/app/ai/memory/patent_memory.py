from mem0 import Memory
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
import logging
import hashlib

logger = logging.getLogger(__name__)

class PatentAnalysisMemory:
    """
    Mem0-based memory system for patent analysis with cross-session learning.
    Handles document-specific context, historical patterns, and agent corrections.
    """
    
    def __init__(self):
        try:
            # Initialize Mem0 with Chroma configuration for reliable vector storage
            # Using local file storage matching official documentation
            config = {
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": "mem0",
                        "path": "db"
                    }
                }
            }
            
            self.memory = Memory.from_config(config)
            
            # Ensure the collection exists by adding an initialization memory
            # This will auto-create the collection if it doesn't exist
            try:
                # Try with system_init user to check if memory is working
                test_memories = self.memory.get_all(user_id="system_init")
                logger.info(f"PatentAnalysisMemory collection verified with {len(test_memories)} existing memories")
            except Exception as get_error:
                # If no memories exist for system_init, that's fine - memory system is working
                logger.info(f"Memory system ready - no existing system memories found: {get_error}")
            except Exception as collection_error:
                logger.info(f"Collection doesn't exist yet, creating it by adding initialization entry: {collection_error}")
                try:
                    # Force collection creation by adding an initialization entry
                    self.memory.add(
                        "System initialization - PatentAnalysisMemory started",
                        user_id="system_init",
                        metadata={
                            "type": "system_initialization",
                            "timestamp": datetime.now().isoformat(),
                            "purpose": "Create collection on first startup"
                        }
                    )
                    logger.info("✅ Collection created successfully with initialization entry")
                except Exception as init_error:
                    logger.error(f"Failed to create collection: {init_error}")
                    # Don't raise error, let system continue and try again during actual usage
            
            logger.info("PatentAnalysisMemory initialized with Chroma vector store (v1.0+) for persistent storage")
                
        except Exception as e:
            logger.error(f"Failed to initialize PatentAnalysisMemory: {e}")
            raise

    def store_agent_findings(
        self,
        document_id: str,
        agent_name: str,
        findings: Dict[str, Any],
        metadata: Optional[Dict] = None
    ) -> bool:
        """Store findings from a specific agent in shared memory"""
        try:
            # Create summary text for semantic search
            summary = self._create_findings_summary(agent_name, findings)

            # Store findings using correct Mem0 API format with unique user_id per agent
            unique_user_id = f"{document_id}_{agent_name}"  # Unique user_id to prevent deduplication
            self.memory.add(
                summary,  # First positional parameter is the content
                user_id=unique_user_id,  # Use unique user_id per agent to prevent overwrites
                metadata={
                    "type": "agent_findings",
                    "agent": agent_name,
                    "document_id": document_id,
                    "findings": json.dumps(findings),  # Convert dict to JSON string for v1.0.0b0
                    "confidence": findings.get("confidence", 0.0),
                    "issues_count": len(findings.get("issues", [])),
                    "timestamp": datetime.now().isoformat(),
                    "content_hash": hashlib.md5(str(findings).encode()).hexdigest(),
                    **(metadata or {})
                }
            )

            logger.info(f"Stored findings for agent {agent_name} on document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store agent findings: {e}")
            return False

    def get_shared_analysis_context(
        self,
        document_id: str,
        requesting_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all analysis context from shared memory for current workflow"""
        try:
            # Get all memories for this document - try multiple approaches
            results = []

            # Try to get memories for each agent in the document (v1.0.0b0 requires user_id)
            agent_types = ['structure', 'legal', 'quality']
            try:
                results = []
                for agent_type in agent_types:
                    user_id = f"{document_id}_{agent_type}"
                    try:
                        agent_results = self.memory.get_all(user_id=user_id)
                        results.extend(agent_results)
                    except:
                        continue  # Agent hasn't stored findings yet
            except Exception as e:
                logger.debug(f"Memory retrieval failed: {e}")

            # Extract findings from metadata (not JSON parsing)
            context = {
                "document_id": document_id,
                "agent_findings": {},
                "cross_agent_insights": [],
                "historical_patterns": []
            }

            for i, result in enumerate(results):
                try:
                    # Handle Mem0 response format (dict with metadata key)
                    if isinstance(result, dict) and 'metadata' in result:
                        metadata = result['metadata']

                        if metadata and metadata.get('type') == 'agent_findings':
                            agent = metadata.get('agent')
                            findings_json = metadata.get('findings', '{}')

                            if agent and findings_json:
                                try:
                                    # Parse JSON string back to dict object for v1.0.0b0
                                    if isinstance(findings_json, str):
                                        findings = json.loads(findings_json)
                                    else:
                                        findings = findings_json

                                    context['agent_findings'][agent] = findings
                                    logger.debug(f"Retrieved {agent} findings with {len(findings.get('issues', []))} issues")
                                except (json.JSONDecodeError, TypeError) as e:
                                    logger.warning(f"Failed to parse {agent} findings: {e}")
                                    continue

                except Exception as e:
                    logger.warning(f"Failed to extract findings from memory entry: {e}")
                    continue

            # Generate cross-agent insights
            context['cross_agent_insights'] = self._generate_cross_agent_insights(context['agent_findings'])

            logger.info(f"Retrieved shared context with {len(context['agent_findings'])} agent findings")
            return context

        except Exception as e:
            logger.error(f"Failed to get shared analysis context: {e}")
            return {"document_id": document_id, "agent_findings": {}, "cross_agent_insights": [], "historical_patterns": []}

    def store_cross_agent_insight(
        self,
        document_id: str,
        insight: Dict[str, Any]
    ) -> bool:
        """Store insights that emerge from cross-agent analysis"""
        try:
            insight_summary = f"Cross-agent insight: {insight.get('type', 'general')} - {insight.get('description', '')}"

            self.memory.add(
                insight_summary,  # First positional parameter is the content
                user_id=document_id,
                metadata={
                    "type": "cross_agent_insight",
                    "document_id": document_id,
                    "insight": json.dumps(insight),  # Convert dict to JSON string
                    "agents_involved": json.dumps(insight.get('agents', [])),  # Convert list to JSON string
                    "confidence": insight.get('confidence', 0.0),
                    "timestamp": datetime.now().isoformat()
                }
            )

            logger.info(f"Stored cross-agent insight for document {document_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store cross-agent insight: {e}")
            return False

    def get_similar_cases(
        self,
        document_characteristics: Dict[str, Any]
    ) -> List[Dict]:
        """Find similar patent analyses from global memory"""
        try:
            # Extract search terms from document characteristics
            search_terms = []
            if 'domain' in document_characteristics:
                search_terms.append(document_characteristics['domain'])
            if 'patent_type' in document_characteristics:
                search_terms.append(document_characteristics['patent_type'])

            query = f"patent analysis {' '.join(search_terms)}".strip()

            # Search across global memory (all documents)
            try:
                # Get all memories from global storage directly
                global_results = self.memory.get_all(user_id="global_memory")

                # Filter by search terms in the content
                results = []
                for result in global_results:
                    content = result.get('memory', '').lower()
                    if any(term.lower() in content for term in search_terms) or not search_terms:
                        results.append(result)

                logger.debug(f"Found {len(results)} similar cases from global memory")
            except Exception as e:
                logger.debug(f"Global memory retrieval failed, using search: {e}")
                results = self.memory.search(
                    query=query,
                    user_id="global_memory",  # Search in global memory
                    limit=50
                )

            # Extract similar cases from metadata
            similar_cases = []
            for result in results:
                try:
                    if isinstance(result, dict) and 'metadata' in result:
                        metadata = result['metadata']
                        if metadata and metadata.get('type') == 'analysis_summary':
                            analysis_summary = metadata.get('analysis_summary', {})

                            # FIX: Parse JSON string back to dict (was stored as json.dumps)
                            if isinstance(analysis_summary, str):
                                analysis_summary = json.loads(analysis_summary)

                            if analysis_summary:
                                similar_cases.append(analysis_summary)
                except Exception as e:
                    continue

            logger.info(f"Found {len(similar_cases)} similar cases")
            return similar_cases

        except Exception as e:
            logger.error(f"Failed to get similar cases: {e}")
            return []

    def store_cross_validation_result(
        self,
        document_id: str,
        conflicts: List[Dict],
        resolutions: List[Dict]
    ) -> bool:
        """Store cross-agent validation results"""
        try:
            # Fix Mem0 API call
            validation_text = f"Cross-validation for document {document_id}: {len(conflicts)} conflicts, {len(resolutions)} resolutions. Details: {json.dumps({'conflicts': conflicts, 'resolutions': resolutions})}"
            
            self.memory.add(
                validation_text,  # First positional parameter is the content
                user_id=document_id,
                metadata={
                    "type": "cross_validation",
                    "document_id": document_id,
                    "conflicts_count": len(conflicts),
                    "resolutions_count": len(resolutions),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Stored cross-validation results for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store cross-validation result: {e}")
            return False

    def store_analysis_summary(
        self,
        document_id: str,
        analysis_summary: Dict[str, Any]
    ) -> bool:
        """Store completed analysis summary for future learning"""
        try:
            logger.info(f"🌍 GLOBAL MEMORY: Starting to store analysis summary for document {document_id}")
            logger.info(f"🌍 GLOBAL MEMORY: Analysis summary keys: {list(analysis_summary.keys())}")

            # Store final analysis summary
            summary_text = f"Complete patent analysis for document {document_id}: score {analysis_summary.get('overall_score', 0.0):.2f}"
            logger.info(f"🌍 GLOBAL MEMORY: Summary text: {summary_text}")

            # Store in global memory for cross-session learning
            self.memory.add(
                summary_text,  # First positional parameter is the content
                user_id="global_memory",
                metadata={
                    "document_id": document_id,
                    "patent_type": analysis_summary.get("patent_type", "unknown"),
                    "domain": analysis_summary.get("domain", "unknown"),
                    "analysis_date": datetime.now().isoformat(),
                    "overall_score": analysis_summary.get("overall_score", 0.0),
                    "type": "analysis_summary",
                    "analysis_summary": json.dumps(analysis_summary)  # Convert dict to JSON string
                }
            )

            logger.info(f"🌍 GLOBAL MEMORY: ✅ Successfully stored analysis summary for document {document_id}")

            # Verify storage immediately
            try:
                global_results = self.memory.get_all(user_id="global_memory")
                logger.info(f"🌍 GLOBAL MEMORY: Verification - found {len(global_results)} total global memories")
            except Exception as ve:
                logger.warning(f"🌍 GLOBAL MEMORY: Could not verify storage: {ve}")

            return True
            
        except Exception as e:
            logger.error(f"🌍 GLOBAL MEMORY: ❌ Failed to store analysis summary: {e}")
            import traceback
            logger.error(f"🌍 GLOBAL MEMORY: ❌ Full traceback: {traceback.format_exc()}")
            return False

    def store_correction_pattern(
        self, 
        agent_name: str, 
        pattern: Dict[str, Any]
    ) -> bool:
        """Store correction patterns for agent learning"""
        try:
            # Store correction pattern
            correction_text = f"Correction pattern for {agent_name}: {pattern.get('type', 'general')} with effectiveness {pattern.get('effectiveness', 1.0):.2f}"

            self.memory.add(
                correction_text,  # First positional parameter is the content
                user_id="global_memory",
                metadata={
                    "agent": agent_name,
                    "pattern_type": pattern["type"],
                    "correction_date": datetime.now().isoformat(),
                    "effectiveness": pattern.get("effectiveness", 1.0),
                    "type": "correction_pattern"
                }
            )
            
            logger.info(f"Stored correction pattern for agent {agent_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store correction pattern: {e}")
            return False

    def get_agent_correction_patterns(
        self, 
        agent_name: str
    ) -> List[Dict]:
        """Get correction patterns for specific agent"""
        try:
            # Get correction patterns from global memory with updated API
            try:
                # Get all memories from global storage directly
                global_results = self.memory.get_all(user_id="global_memory")

                patterns = []
                for result in global_results:
                    if isinstance(result, dict) and 'metadata' in result:
                        metadata = result['metadata']
                        if (metadata and metadata.get('type') == 'correction_pattern' and
                            metadata.get('agent') == agent_name):
                            patterns.append(result)

                logger.debug(f"Found {len(patterns)} correction patterns for {agent_name}")
            except Exception as e:
                logger.debug(f"Pattern retrieval failed, using search: {e}")
                patterns = self.memory.search(
                    query=f"correction pattern {agent_name}",
                    user_id="global_memory",
                    limit=20
                )

            parsed_patterns = []
            for pattern in patterns:
                try:
                    if isinstance(pattern, dict) and 'metadata' in pattern:
                        metadata = pattern['metadata']
                        if (metadata and metadata.get('type') == 'correction_pattern' and
                            metadata.get('agent') == agent_name):
                            pattern_data = metadata.get('pattern', {})
                            if pattern_data:
                                parsed_patterns.append(pattern_data)
                except Exception as e:
                    continue
                    
            logger.info(f"Retrieved {len(parsed_patterns)} correction patterns for agent {agent_name}")
            return parsed_patterns
            
        except Exception as e:
            logger.error(f"Failed to get correction patterns for {agent_name}: {e}")
            return []

    def _create_findings_summary(self, agent_name: str, findings: Dict[str, Any]) -> str:
        """Create a unique searchable summary of agent findings"""
        confidence = findings.get('confidence', 0.0)
        issues_count = len(findings.get('issues', []))
        finding_type = findings.get('type', 'analysis')

        # Generate unique timestamp to prevent deduplication
        import time
        unique_timestamp = int(time.time() * 1000000)  # microsecond precision

        # Create agent-specific unique identifiers and content
        agent_specific_content = []

        if agent_name == 'structure':
            agent_specific_content.extend([
                f"Structure analysis performed at {unique_timestamp}",
                f"Document formatting assessment: {confidence:.3f} confidence",
                f"Structural issues detected: {issues_count}"
            ])
        elif agent_name == 'legal':
            agent_specific_content.extend([
                f"Legal compliance analysis at {unique_timestamp}",
                f"Legal review confidence: {confidence:.3f}",
                f"Legal issues found: {issues_count}"
            ])
        else:
            agent_specific_content.extend([
                f"{agent_name} agent analysis at {unique_timestamp}",
                f"Analysis confidence: {confidence:.3f}",
                f"Issues identified: {issues_count}"
            ])

        # Add specific findings details to make content unique
        if findings.get('compliance_score'):
            agent_specific_content.append(f"Compliance score: {findings['compliance_score']:.3f}")

        if findings.get('recommendations'):
            rec_count = len(findings['recommendations'])
            agent_specific_content.append(f"Recommendations provided: {rec_count}")
            # Add first few words of first recommendation for uniqueness
            if rec_count > 0 and isinstance(findings['recommendations'][0], str):
                first_rec = findings['recommendations'][0][:30]
                agent_specific_content.append(f"First rec: {first_rec}")

        if findings.get('issues'):
            for i, issue in enumerate(findings['issues'][:2]):  # First 2 issues for uniqueness
                if isinstance(issue, dict):
                    issue_type = issue.get('type', 'unknown')
                    agent_specific_content.append(f"Issue {i+1} type: {issue_type}")

        # Create unique content with agent name prefix and unique details
        unique_content = f"AGENT_{agent_name.upper()}_FINDINGS_{unique_timestamp}: " + " | ".join(agent_specific_content)

        return unique_content

    def _generate_cross_agent_insights(self, agent_findings: Dict[str, Dict]) -> List[Dict]:
        """Generate insights from multiple agent findings"""
        insights = []

        # Example: Compare confidence levels between agents
        if len(agent_findings) >= 2:
            agents = list(agent_findings.keys())
            confidences = [findings.get('confidence', 0.0) for findings in agent_findings.values()]

            if max(confidences) - min(confidences) > 0.3:
                insights.append({
                    'type': 'confidence_divergence',
                    'description': f'Significant confidence difference between {agents[0]} and {agents[1]}',
                    'agents': agents,
                    'confidence': 0.8
                })

        # Example: Cross-validate issue counts
        total_issues = sum(len(findings.get('issues', [])) for findings in agent_findings.values())
        if total_issues > 0:
            insights.append({
                'type': 'issue_aggregation',
                'description': f'Total {total_issues} issues found across all agents',
                'agents': list(agent_findings.keys()),
                'confidence': 0.9
            })

        return insights

    def get_workflow_progress(self, document_id: str) -> Dict[str, Any]:
        """Get current workflow progress from memory"""
        try:
            # Get workflow progress using updated API
            try:
                # Get all memories for this document directly
                doc_results = self.memory.get_all(user_id=document_id)

                progress = {
                    "completed_agents": [],
                    "current_phase": "unknown",
                    "total_issues": 0,
                    "overall_confidence": 0.0
                }

                agent_confidences = []
                total_issues = 0

                for result in doc_results:
                    try:
                        if isinstance(result, dict) and 'metadata' in result:
                            metadata = result['metadata']
                            if metadata and metadata.get('type') == 'agent_findings':
                                agent = metadata.get('agent')
                                findings = metadata.get('findings', {})

                                if agent and findings:
                                    if agent not in progress['completed_agents']:
                                        progress['completed_agents'].append(agent)
                                    agent_confidences.append(findings.get('confidence', 0.0))
                                    total_issues += len(findings.get('issues', []))

                            elif metadata and metadata.get('type') == 'workflow_progress':
                                progress['current_phase'] = metadata.get('phase', 'unknown')

                    except Exception as e:
                        continue

                logger.debug(f"Workflow progress: {len(progress['completed_agents'])} agents completed")
            except Exception as e:
                logger.debug(f"Progress retrieval failed: {e}")
                results = self.memory.search(
                    query="agent findings",
                    user_id=document_id,
                    limit=50
                )

                progress = {
                    "completed_agents": [],
                    "current_phase": "unknown",
                    "total_issues": 0,
                    "overall_confidence": 0.0
                }

                agent_confidences = []
                total_issues = 0

                for result in results:
                    try:
                        if isinstance(result, dict) and 'metadata' in result:
                            metadata = result['metadata']
                            if metadata and metadata.get('type') == 'agent_findings':
                                agent = metadata.get('agent')
                                findings = metadata.get('findings', {})

                                if agent and findings:
                                    if agent not in progress['completed_agents']:
                                        progress['completed_agents'].append(agent)
                                    agent_confidences.append(findings.get('confidence', 0.0))
                                    total_issues += len(findings.get('issues', []))

                    except Exception as e:
                        continue

            progress['total_issues'] = total_issues
            if agent_confidences:
                progress['overall_confidence'] = sum(agent_confidences) / len(agent_confidences)

            return progress

        except Exception as e:
            logger.error(f"Failed to get workflow progress: {e}")
            return {"completed_agents": [], "current_phase": "unknown", "total_issues": 0, "overall_confidence": 0.0}

    def store_workflow_progress(
        self,
        document_id: str,
        phase: str,
        progress_data: Dict[str, Any]
    ) -> bool:
        """Store workflow progress in memory"""
        try:
            progress_summary = f"Workflow phase {phase}: {progress_data.get('message', 'In progress')}"

            self.memory.add(
                progress_summary,  # First positional parameter is the content
                user_id=document_id,
                metadata={
                    "type": "workflow_progress",
                    "document_id": document_id,
                    "phase": phase,
                    "progress_data": json.dumps(progress_data),  # Convert dict to JSON string
                    "timestamp": datetime.now().isoformat()
                }
            )

            logger.info(f"Stored workflow progress for document {document_id}, phase {phase}")
            return True

        except Exception as e:
            logger.error(f"Failed to store workflow progress: {e}")
            return False

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        try:
            # This would need to be implemented based on Mem0's API
            # For now, return basic stats
            return {
                "status": "active",
                "timestamp": datetime.now().isoformat(),
                "message": "Memory system operational"
            }
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"status": "error", "message": str(e)}
