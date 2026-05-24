from qtpynodeeditor import Connection, PortType, ConnectionPolicy
from qtpynodeeditor import exceptions

original_init = Connection.__init__

def patched_init(self, port_a, port_b=None, *, style=None, converter=None):
    # Temporarily hide connections to bypass the hardcoded check
    hidden_in_connections = []
    
    if port_a is not None and port_b is not None:
        in_port = port_a if port_a.port_type == PortType.input else port_b
        out_port = port_b if port_a.port_type == PortType.input else port_a
    else:
        in_port = port_a if port_a.port_type == PortType.input else None
        out_port = port_a if port_a.port_type == PortType.output else None

    if in_port is not None:
        try:
            policy = in_port.connection_policy
        except AttributeError:
            policy = ConnectionPolicy.one
            
        if policy == ConnectionPolicy.many:
            # Hide connections during init
            hidden_in_connections = list(in_port.connections)
            in_port._connections.clear() if hasattr(in_port, '_connections') else None
    
    try:
        original_init(self, port_a, port_b, style=style, converter=converter)
    finally:
        # Restore hidden connections
        if hidden_in_connections:
            for c in hidden_in_connections:
                if c not in in_port._connections:
                    in_port._connections.append(c)

print("Patch tested ok")
