"""
Workflow engine for Enterprise PM Agent
Supports multiple methodologies through configuration-driven state machines
"""

from typing import Dict, List, Optional, Any, Callable, Set
from enum import Enum
from dataclasses import dataclass, field
import json
import uuid
from datetime import datetime
from pydantic import BaseModel as PydanticModel, Field

from persistence.storage import BaseEntity, StorageResult


class TriggerType(str, Enum):
    """Types of triggers that can cause state transitions"""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    TIME_BASED = "time_based"
    EVENT_BASED = "event_based"


class ActionType(str, Enum):
    """Types of actions that can be performed during transitions"""
    NOTIFY = "notify"
    UPDATE_FIELD = "update_field"
    CREATE_ENTITY = "create_entity"
    EXTERNAL_API = "external_api"
    CUSTOM_SCRIPT = "custom_script"


@dataclass
class Action:
    """Action to be executed during a transition"""
    action_type: ActionType
    configuration: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None  # JavaScript-like expression for conditional execution


@dataclass
class Trigger:
    """Trigger that can initiate a transition"""
    trigger_type: TriggerType
    configuration: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None  # Condition that must be met for trigger to fire


@dataclass
class Transition:
    """Defines a transition between states"""
    # Fields without defaults first
    name: str
    from_state: str
    to_state: str
    trigger: Trigger
    # Fields with defaults after
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    actions: List[Action] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)  # Conditions that must be true for transition
    required_fields: List[str] = field(default_factory=list)  # Fields that must be present
    permission: Optional[str] = None  # Permission required to execute this transition


@dataclass
class State:
    """Defines a state in the workflow"""
    # Fields without defaults first
    name: str
    # Fields with defaults after
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: Optional[str] = None
    is_initial: bool = False
    is_final: bool = False
    permissions: List[str] = field(default_factory=list)  # Permissions required to be in this state
    entry_actions: List[Action] = field(default_factory=list)  # Actions on entering state
    exit_actions: List[Action] = field(default_factory=list)  # Actions on leaving state


@dataclass
class WorkflowDefinition:
    """Complete workflow definition"""
    # Fields without defaults first
    name: str
    methodology: str  # waterfall, scrum, safe, etc.
    # Fields with defaults after
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: Optional[str] = None
    version: str = "1.0"
    entities: List[str] = field(default_factory=list)  # Entity types this workflow applies to
    states: List[State] = field(default_factory=list)
    transitions: List[Transition] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class WorkflowInstance(BaseEntity):
    """Runtime instance of a workflow"""
    workflow_id: str
    entity_id: str  # ID of the entity this workflow is tracking
    current_state: str
    history: List[Dict[str, Any]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)  # Custom data for this instance
    is_active: bool = True
    completed_at: Optional[datetime] = None


class WorkflowEngine:
    """Core workflow engine that manages workflow instances and transitions"""

    def __init__(self):
        self.workflow_definitions: Dict[str, WorkflowDefinition] = {}
        self.workflow_instances: Dict[str, WorkflowInstance] = {}
        # In a real implementation, these would use storage adapters
        self._definition_storage = None
        self._instance_storage = None

    def register_workflow(self, workflow: WorkflowDefinition) -> bool:
        """Register a workflow definition"""
        try:
            self.workflow_definitions[workflow.id] = workflow
            # In production, would save to storage
            return True
        except Exception:
            return False

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get a workflow definition by ID"""
        return self.workflow_definitions.get(workflow_id)

    def list_workflows(self) -> List[WorkflowDefinition]:
        """List all registered workflow definitions"""
        return list(self.workflow_definitions.values())

    async def start_workflow(
        self,
        workflow_id: str,
        entity_id: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start a new workflow instance for an entity"""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        # Find initial state
        initial_state = None
        for state in workflow.states:
            if state.is_initial:
                initial_state = state
                break

        if not initial_state:
            # If no explicit initial state, use first state
            if workflow.states:
                initial_state = workflow.states[0]
            else:
                raise ValueError(f"No states defined in workflow {workflow_id}")

        # Create workflow instance
        instance_id = str(uuid.uuid4())
        instance = WorkflowInstance(
            id=instance_id,
            workflow_id=workflow_id,
            entity_id=entity_id,
            current_state=initial_state.name,
            context=initial_context or {}
        )

        # Execute entry actions for initial state
        await self._execute_actions(initial_state.entry_actions, {
            "workflow_instance": instance,
            "entity_id": entity_id,
            "context": instance.context
        })

        # Store instance
        self.workflow_instances[instance_id] = instance

        # Add to history
        await self._add_history_entry(
            instance_id,
            "workflow_started",
            {
                "workflow_id": workflow_id,
                "initial_state": initial_state.name,
                "context": initial_context or {}
            }
        )

        return instance_id

    async def transition(
        self,
        instance_id: str,
        transition_id: str,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Execute a transition on a workflow instance"""
        # Get workflow instance
        instance = self.workflow_instances.get(instance_id)
        if not instance:
            raise ValueError(f"Workflow instance not found: {instance_id}")

        if not instance.is_active:
            raise ValueError(f"Workflow instance is not active: {instance_id}")

        # Get workflow definition
        workflow = self.get_workflow(instance.workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {instance.workflow_id}")

        # Find transition
        transition = None
        for t in workflow.transitions:
            if t.id == transition_id:
                transition = t
                break

        if not transition:
            raise ValueError(f"Transition not found: {transition_id}")

        # Validate transition can be applied
        if not await self._can_transition(instance, transition, user_id):
            return False

        # Evaluate conditions
        if not await self._evaluate_conditions(transition.conditions, instance, context):
            return False

        # Check required fields
        if not await self._check_required_fields(transition.required_fields, instance):
            return False

        # Execute exit actions from current state
        current_state = self._get_state_by_name(workflow, instance.current_state)
        if current_state:
            await self._execute_actions(current_state.exit_actions, {
                "workflow_instance": instance,
                "entity_id": instance.entity_id,
                "context": instance.context
            })

        # Execute transition actions
        await self._execute_actions(transition.actions, {
            "workflow_instance": instance,
            "entity_id": instance.entity_id,
            "user_id": user_id,
            "context": context or {}
        })

        # Get target state
        target_state = self._get_state_by_name(workflow, transition.to_state)
        if not target_state:
            raise ValueError(f"Target state not found: {transition.to_state}")

        # Update instance
        old_state = instance.current_state
        instance.current_state = target_state.name
        instance.updated_at = datetime.utcnow()

        # Execute entry actions for new state
        await self._execute_actions(target_state.entry_actions, {
            "workflow_instance": instance,
            "entity_id": instance.entity_id,
            "context": instance.context
        })

        # Add to history
        await self._add_history_entry(
            instance_id,
            "transition_executed",
            {
                "transition_id": transition.id,
                "transition_name": transition.name,
                "from_state": old_state,
                "to_state": target_state.name,
                "user_id": user_id,
                "context": context or {}
            }
        )

        # Check if we've reached a final state
        if target_state.is_final:
            instance.is_active = False
            instance.completed_at = datetime.utcnow()
            await self._add_history_entry(
                instance_id,
                "workflow_completed",
                {
                    "completed_at": instance.completed_at.isoformat()
                }
            )

        return True

    async def get_available_transitions(
        self,
        instance_id: str,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of available transitions for a workflow instance"""
        instance = self.workflow_instances.get(instance_id)
        if not instance:
            return []

        workflow = self.get_workflow(instance.workflow_id)
        if not workflow:
            return []

        available = []
        for transition in workflow.transitions:
            if transition.from_state == instance.current_state:
                # Check if user can execute this transition
                if await self._can_transition(instance, transition, user_id):
                    available.append({
                        "id": transition.id,
                        "name": transition.name,
                        "to_state": transition.to_state,
                        "description": getattr(transition, 'description', ''),
                        "required_fields": transition.required_fields
                    })

        return available

    def get_workflow_history(self, instance_id: str) -> List[Dict[str, Any]]:
        """Get the history of a workflow instance"""
        # In a real implementation, this would come from storage
        # For now, we'll return an empty list as history is stored in the instance
        instance = self.workflow_instances.get(instance_id)
        if not instance:
            return []

        # Return history from instance (simplified)
        return [
            {
                "timestamp": entry.get("timestamp", ""),
                "event_type": entry.get("event_type", ""),
                "details": entry.get("details", {})
            }
            for entry in getattr(instance, '_history', [])
        ]

    # Private helper methods

    def _get_state_by_name(self, workflow: WorkflowDefinition, state_name: str) -> Optional[State]:
        """Get a state by its name"""
        for state in workflow.states:
            if state.name == state_name:
                return state
        return None

    async def _can_transition(
        self,
        instance: WorkflowInstance,
        transition: Transition,
        user_id: Optional[str]
    ) -> bool:
        """Check if a transition can be executed"""
        # Check if workflow is active
        if not instance.is_active:
            return False

        # Check if transition matches current state
        if transition.from_state != instance.current_state:
            return False

        # Check permissions if specified
        if transition.permission and user_id:
            # In a real implementation, would check user permissions
            # For now, we'll assume the user has the permission
            pass

        return True

    async def _evaluate_conditions(
        self,
        conditions: List[str],
        instance: WorkflowInstance,
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """Evaluate conditions for a transition"""
        # In a real implementation, would evaluate expressions
        # For now, we'll assume all conditions are met
        return len(conditions) == 0 or True

    async def _check_required_fields(
        self,
        required_fields: List[str],
        instance: WorkflowInstance
    ) -> bool:
        """Check if required fields are present in the entity context"""
        # In a real implementation, would check the actual entity data
        # For now, we'll assume all required fields are present
        return len(required_fields) == 0 or True

    async def _execute_actions(
        self,
        actions: List[Action],
        context: Dict[str, Any]
    ):
        """Execute a list of actions"""
        for action in actions:
            # Check condition if specified
            if action.condition:
                # In a real implementation, would evaluate the condition
                # For now, we'll assume the condition is met
                pass

            # Execute action based on type
            if action.action_type == ActionType.NOTIFY:
                await self._execute_notify_action(action, context)
            elif action.action_type == ActionType.UPDATE_FIELD:
                await self._execute_update_field_action(action, context)
            elif action.action_type == ActionType.CREATE_ENTITY:
                await self._execute_create_entity_action(action, context)
            elif action.action_type == ActionType.EXTERNAL_API:
                await self._execute_external_api_action(action, context)
            elif action.action_type == ActionType.CUSTOM_SCRIPT:
                await self._execute_custom_script_action(action, context)

    async def _execute_notify_action(
        self,
        action: Action,
        context: Dict[str, Any]
    ):
        """Execute a notification action"""
        # Implementation would send notifications (email, slack, etc.)
        # For now, we'll just log
        print(f"[NOTIFICATION] {action.configuration.get('message', 'Notification sent')}")

    async def _execute_update_field_action(
        self,
        action: Action,
        context: Dict[str, Any]
    ):
        """Execute a field update action"""
        # Implementation would update fields on the entity
        # For now, we'll just log
        field = action.configuration.get('field')
        value = action.configuration.get('value')
        print(f"[UPDATE_FIELD] Setting {field} = {value}")

    async def _execute_create_entity_action(
        self,
        action: Action,
        context: Dict[str, Any]
    ):
        """Execute an entity creation action"""
        # Implementation would create a new entity
        # For now, we'll just log
        entity_type = action.configuration.get('entity_type')
        print(f"[CREATE_ENTITY] Creating {entity_type}")

    async def _execute_external_api_action(
        self,
        action: Action,
        context: Dict[str, Any]
    ):
        """Execute an external API call action"""
        # Implementation would call an external API
        # For now, we'll just log
        url = action.configuration.get('url')
        method = action.configuration.get('method', 'GET')
        print(f"[EXTERNAL_API] {method} {url}")

    async def _execute_custom_script_action(
        self,
        action: Action,
        context: Dict[str, Any]
    ):
        """Execute a custom script action"""
        # In a real implementation, would execute a sandboxed script
        # For now, we'll just log
        script = action.configuration.get('script')
        print(f"[CUSTOM_SCRIPT] Executing script: {script[:50]}...")

    async def _add_history_entry(
        self,
        instance_id: str,
        event_type: str,
        details: Dict[str, Any]
    ):
        """Add an entry to the workflow history"""
        instance = self.workflow_instances.get(instance_id)
        if instance:
            if not hasattr(instance, '_history'):
                instance._history = []

            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "details": details
            }
            instance._history.append(entry)


# Global workflow engine instance
workflow_engine = WorkflowEngine()


# Example workflow definitions for common methodologies

def create_waterfall_workflow() -> WorkflowDefinition:
    """Create a standard waterfall workflow"""
    workflow = WorkflowDefinition(
        name="Waterfall Development",
        description="Traditional waterfall methodology with sequential phases",
        methodology="waterfall"
    )

    # Define states
    requirements = State(
        name="Requirements Gathering",
        description="Collecting and documenting requirements",
        is_initial=True
    )

    design = State(
        name="System Design",
        description="Creating system architecture and design documents"
    )

    implementation = State(
        name="Implementation",
        description="Writing code and unit tests"
    )

    testing = State(
        name="Testing",
        description="Verifying the system meets requirements"
    )

    deployment = State(
        name="Deployment",
        description="Releasing the system to production",
        is_final=True
    )

    maintenance = State(
        name="Maintenance",
        description="Ongoing support and bug fixes",
        is_final=True
    )

    workflow.states = [requirements, design, implementation, testing, deployment, maintenance]

    # Define transitions
    workflow.transitions = [
        Transition(
            name="Start Design",
            from_state="Requirements Gathering",
            to_state="System Design",
            trigger=Trigger(
                trigger_type=TriggerType.MANUAL,
                configuration={}
            ),
            actions=[
                Action(
                    action_type=ActionType.NOTIFY,
                    configuration={
                        "message": "Moving from Requirements to Design phase"
                    }
                )
            ]
        ),
        Transition(
            name="Start Implementation",
            from_state="System Design",
            to_state="Implementation",
            trigger=Trigger(
                trigger_type=TriggerType.MANUAL,
                configuration={}
            )
        ),
        Transition(
            name="Start Testing",
            from_state="Implementation",
            to_state="Testing",
            trigger=Trigger(
                trigger_type=TriggerType.MANUAL,
                configuration={}
            )
        ),
        Transition(
            name="Deploy to Production",
            from_state="Testing",
            to_state="Deployment",
            trigger=Trigger(
                trigger_type=TriggerType.MANUAL,
                configuration={}
            ),
            actions=[
                Action(
                    action_type=ActionType.NOTIFY,
                    configuration={
                        "message": "Deployment to production initiated"
                    }
                )
            ]
        ),
        Transition(
            name="Enter Maintenance",
            from_state="Deployment",
            to_state="Maintenance",
            trigger=Trigger(
                trigger_type=TriggerType.AUTOMATIC,
                configuration={
                    "delay_days": 1
                }
            )
        )
    ]

    return workflow


def create_scrum_workflow() -> WorkflowDefinition:
    """Create a Scrum workflow"""
    workflow = WorkflowDefinition(
        name="Scrum Development",
        description="Agile Scrum methodology with sprints",
        methodology="scrum"
    )

    # Define states
    backlog = State(
        name="Product Backlog",
        description="Items waiting to be prioritized",
        is_initial=True
    )

    sprint_backlog = State(
        name="Sprint Backlog",
        description="Items committed for current sprint"
    )

    in_progress = State(
        name="In Progress",
        description="Work actively being performed"
    )

    review = State(
        name="Sprint Review",
        description="Reviewing completed work with stakeholders"
    )

    retrospective = State(
        name="Sprint Retrospective",
        description="Team reflects on the sprint"
    )

    done = State(
        name="Done",
        description="Work completed and accepted",
        is_final=True
    )

    workflow.states = [backlog, sprint_backlog, in_progress, review, retrospective, done]

    # Define transitions
    workflow.transitions = [
        Transition(
            name="Plan Sprint",
            from_state="Product Backlog",
            to_state="Sprint Backlog",
            trigger=Trigger(
                trigger_type=TriggerType.MANUAL,
                configuration={}
            )
        ),
        Transition(
            name="Start Work",
            from_state="Sprint Backlog",
            to_state="In Progress",
            trigger=Trigger(
                trigger_type=TriggerType.MANUAL,
                configuration={}
            )
        ),
        Transition(
            name="Complete Work",
            from_state="In Progress",
            to_state="Sprint Review",
            trigger=Trigger(
                trigger_type=TriggerType.MANUAL,
                configuration={}
            )
        ),
        Transition(
            name="Review Sprint",
            from_state="Sprint Review",
            to_state="Sprint Retrospective",
            trigger=Trigger(
                trigger_type=TriggerType.MANUAL,
                configuration={}
            )
        ),
        Transition(
            name="Retrospective",
            from_state="Sprint Retrospective",
            to_state="Product Backlog",
            trigger=Trigger(
                trigger_type=TriggerType.MANUAL,
                configuration={}
            ),
            actions=[
                Action(
                    action_type=ActionType.NOTIFY,
                    configuration={
                        "message": "Sprint retrospective completed - ready for next sprint planning"
                    }
                )
            ]
        ),
        Transition(
            name="Mark Done",
            from_state="Sprint Review",
            to_state="Done",
            trigger=Trigger(
                trigger_type=TriggerType.MANUAL,
                configuration={}
            )
        )
    ]

    return workflow


def register_default_workflows():
    """Register the default workflow templates"""
    workflow_engine.register_workflow(create_waterfall_workflow())
    workflow_engine.register_workflow(create_scrum_workflow())
    # Additional workflows would be registered here


# Auto-register default workflows when module is imported
register_default_workflows()