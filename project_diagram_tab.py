from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLineEdit, QListWidget, QListWidgetItem, 
                               QMessageBox, QSplitter, QInputDialog, QLabel, QDialog,
                               QDialogButtonBox, QMenu, QCompleter, QComboBox, QFileDialog)
from PySide6.QtCore import Qt, Slot, QByteArray, QObject, QEvent
import os
import json

from qtpynodeeditor import (FlowScene, FlowView, DataModelRegistry, 
                            NodeDataModel, PortType, NodeDataType,
                            ConnectionPolicy)
from qtpynodeeditor.port import Port
from qtpynodeeditor.node_painter import NodePainter
from qtpynodeeditor.node_geometry import NodeGeometry
from qtpynodeeditor.connection_painter import ConnectionPainter
from qtpy.QtGui import QPolygonF, QPen, QPixmap, QColor, QImage, QPainter
from qtpy.QtCore import QPointF, QSize, QRectF
import math
HAS_NODE_EDITOR = True

# --- Patch for Port Connection Policy ---
# This allows models to define policy for both input and output ports
def _fixed_port_connection_policy(self):
    attr_name = 'port_in_connection_policy' if self.port_type == PortType.input else 'port_out_connection_policy'
    val = getattr(self.model, attr_name, None)
    if val is not None:
        if hasattr(val, '__call__'):
            try: return val(self.index)
            except: pass
            try: return val()
            except: pass
        return val
    return ConnectionPolicy.one if self.port_type == PortType.input else ConnectionPolicy.many

Port.connection_policy = property(_fixed_port_connection_policy)

from qtpynodeeditor.connection import Connection
_original_conn_init = Connection.__init__

def _patched_conn_init(self, port_a, port_b=None, **kwargs):
    hidden_in_connections = []
    
    if port_a is not None and port_b is not None:
        in_port = port_a if port_a.port_type == PortType.input else port_b
    else:
        in_port = port_a if port_a and port_a.port_type == PortType.input else None

    if in_port is not None:
        try:
            policy = in_port.connection_policy
        except AttributeError:
            policy = ConnectionPolicy.one
            
        if policy == ConnectionPolicy.many:
            if hasattr(in_port, '_connections'):
                hidden_in_connections = list(in_port._connections)
                in_port._connections.clear()
                
    try:
        _original_conn_init(self, port_a, port_b, **kwargs)
    finally:
        if in_port is not None and hidden_in_connections:
            for c in hidden_in_connections:
                if c not in in_port._connections:
                    in_port._connections.append(c)

Connection.__init__ = _patched_conn_init

# --- Patch for qtpynodeeditor 0.3.3 / PySide6 MRO bug ---
def _fixed_node_data_model_init(self, style=None, parent=None, **kwargs):
    # This patch safely initializes QObject and avoids the object.__init__ TypeError
    try:
        if parent:
            QObject.__init__(self, parent)
        else:
            QObject.__init__(self)
    except TypeError:
        # Ignore cases where QObject is already initialized or doesn't accept the call
        pass
        
    if not hasattr(self, '_style'):
        if style is None:
            from qtpynodeeditor import style as style_module
            style = style_module.default_style
        self._style = style

NodeDataModel.__init__ = _fixed_node_data_model_init

# --- Patch for serialization to avoid recursion ---
def _fixed_flow_scene_getstate__(self):
    data = {"nodes": [], "connections": []}
    
    # Robust iteration over nodes
    nodes_source = self.nodes
    nodes_list = nodes_source.values() if isinstance(nodes_source, dict) else nodes_source
    
    for node in nodes_list:
        node_data = {
            "id": str(node.id),
            "name": node.model.name,
            "position": {"x": node.graphics_object.pos().x(), "y": node.graphics_object.pos().y()},
            "model_data": node.model.save() if hasattr(node.model, 'save') else {}
        }
        data["nodes"].append(node_data)
        
    for conn in self.connections:
        # Use ports directly to be extremely safe
        in_port, out_port = conn.ports
        if in_port and out_port and in_port.node and out_port.node:
            conn_data = {
                "out_id": str(out_port.node.id),
                "out_index": out_port.index,
                "in_id": str(in_port.node.id),
                "in_index": in_port.index
            }
            data["connections"].append(conn_data)
    return data

def _debug_flow_scene_setstate(self, data):
    print("DEBUG: _debug_flow_scene_setstate called")
    self.clear_scene()
    node_map = {}
    
    # Restore nodes
    for node_data in data.get("nodes", []):
        model = self.registry.create(node_data["name"])
        if model:
            node = self.create_node(model)
            node.graphics_object.setPos(QPointF(node_data["position"]["x"], node_data["position"]["y"]))
            if hasattr(model, 'restore'):
                model.restore(node_data.get("model_data", {}))
            node_map[node_data["id"]] = node
            
    # Restore connections
    for conn_data in data.get("connections", []):
        out_node = node_map.get(conn_data["out_id"])
        in_node = node_map.get(conn_data["in_id"])
        if out_node and in_node:
            try:
                # Defensive port retrieval
                def get_ports(node, p_type):
                    state = node.state
                    # Try output_ports/input_ports properties (generators in newer versions)
                    attr = "output_ports" if p_type == PortType.output else "input_ports"
                    val = getattr(state, attr, None)
                    if val is not None:
                        if not hasattr(val, '__call__'):
                            return list(val)
                        else:
                            return list(val())
                    
                    # Fallback to ports() method/property
                    p_attr = getattr(state, "ports", None)
                    if p_attr is not None:
                        if hasattr(p_attr, '__call__'):
                            try: return list(p_attr(p_type))
                            except: pass
                        return [p for p in p_attr if p.port_type == p_type]
                    return []

                outs = get_ports(out_node, PortType.output)
                ins = get_ports(in_node, PortType.input)
                
                if conn_data["out_index"] < len(outs) and conn_data["in_index"] < len(ins):
                    self.create_connection(port_a=outs[conn_data["out_index"]], 
                                         port_b=ins[conn_data["in_index"]])
                else:
                    print(f"Index out of range for connection: out {conn_data['out_index']}/{len(outs)}, in {conn_data['in_index']}/{len(ins)}")
            except Exception as e:
                print(f"Signature error in connection restoration: {e} (Type: {type(e)})")
                import traceback
                traceback.print_exc()

FlowScene.__getstate__ = _fixed_flow_scene_getstate__
FlowScene.__setstate__ = _debug_flow_scene_setstate

# --- Patch for Port Positioning in Diamond Nodes ---
_original_port_scene_position = NodeGeometry.port_scene_position

def _patched_port_scene_position(self, port_type, index, t=None):
    if self._model.name == "DiamondNode":
        if t is None:
            from qtpy.QtGui import QTransform
            t = QTransform()
        
        # Position each of the 4 ports at one of the diamond corners
        w, h = self.width, self.height
        if port_type == PortType.input:
            if index == 0:
                result = QPointF(w/2, 0)      # Top Corner
            else:
                result = QPointF(0, h/2)      # Left Corner
        else:
            if index == 0:
                result = QPointF(w/2, h)      # Bottom Corner
            else:
                result = QPointF(w, h/2)      # Right Corner
        return t.map(result)
    return _original_port_scene_position(self, port_type, index, t)

NodeGeometry.port_scene_position = _patched_port_scene_position

# --- Experimental Patch for Port Shapes (Circles to Triangles) ---
def _patched_draw_connection_points(painter, geom, state, model, scene, node_style, connection_style):
    diameter = node_style.connection_point_diameter
    reduced_diameter = diameter * 0.6
    for port in state.ports:
        scene_pos = port.scene_position
        can_connect = port.can_connect
        port_type = port.port_type
        port_index = port.index
        data_type = port.data_type
        r = 1.0
        
        # Determine shape
        shape = 'circle'
        if hasattr(model, '_port_config'):
            shape = model._port_config.get(port_type, {}).get(port_index, {}).get('shape', 'circle')

        if state.is_reacting and can_connect and port_type == state.reacting_port_type:
            diff = geom.dragging_pos - scene_pos
            dist = math.sqrt(QPointF.dotProduct(diff, diff))
            registry = scene.registry
            dtype1, dtype2 = state.reacting_data_type, data_type
            if port_type != PortType.input:
                dtype2, dtype1 = dtype1, dtype2
            type_convertable = registry.get_type_converter(dtype1, dtype2) is not None
            if dtype1.id == dtype2.id or type_convertable:
                thres = 40.0
                r = ((2.0 - dist / thres) if dist < thres else 1.0)
            else:
                thres = 80.0
                r = ((dist / thres) if dist < thres else 1.0)
        
        color = connection_style.get_normal_color(data_type.id) if connection_style.use_data_defined_colors else node_style.connection_point_color
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        size = reduced_diameter * r
        
        if shape == 'arrow':
            points = [QPointF(scene_pos.x() - size, scene_pos.y() - size),
                      QPointF(scene_pos.x() + size, scene_pos.y()),
                      QPointF(scene_pos.x() - size, scene_pos.y() + size)]
            painter.drawPolygon(QPolygonF(points))
        elif shape == 'many':
            # Y shape / Crows foot
            painter.setPen(QPen(color, 2))
            painter.drawLine(scene_pos.x() - size, scene_pos.y(), scene_pos.x() + size, scene_pos.y())
            painter.drawLine(scene_pos.x() + size, scene_pos.y(), scene_pos.x() - size, scene_pos.y() - size)
            painter.drawLine(scene_pos.x() + size, scene_pos.y(), scene_pos.x() - size, scene_pos.y() + size)
        else:
            painter.drawEllipse(scene_pos, size, size)

def _patched_draw_filled_connection_points(painter, geom, state, model, node_style, connection_style):
    diameter = node_style.connection_point_diameter
    for port in state.ports:
        if not port.connections: continue
        scene_pos = port.scene_position
        port_type = port.port_type
        port_index = port.index
        
        shape = 'circle'
        if hasattr(model, '_port_config'):
            shape = model._port_config.get(port_type, {}).get(port_index, {}).get('shape', 'circle')
            
        color = connection_style.get_normal_color(port.data_type.id) if connection_style.use_data_defined_colors else node_style.filled_connection_point_color
        painter.setPen(color)
        painter.setBrush(color)
        size = diameter * 0.4
        
        if shape == 'arrow':
            points = [QPointF(scene_pos.x() - size, scene_pos.y() - size),
                      QPointF(scene_pos.x() + size, scene_pos.y()),
                      QPointF(scene_pos.x() - size, scene_pos.y() + size)]
            painter.drawPolygon(QPolygonF(points))
        elif shape == 'many':
            painter.setPen(QPen(color, 2))
            painter.drawLine(scene_pos.x() - size, scene_pos.y(), scene_pos.x() + size, scene_pos.y())
            painter.drawLine(scene_pos.x() + size, scene_pos.y(), scene_pos.x() - size, scene_pos.y() - size)
            painter.drawLine(scene_pos.x() + size, scene_pos.y(), scene_pos.x() - size, scene_pos.y() + size)
        else:
            painter.drawEllipse(scene_pos, size, size)

NodePainter.draw_connection_points = staticmethod(_patched_draw_connection_points)
NodePainter.draw_filled_connection_points = staticmethod(_patched_draw_filled_connection_points)

# --- Patch for Connection Line Styles ---
def _patched_draw_normal_line(painter, connection, style):
    if connection.requires_port: return
    
    # Get configuration from output port
    out_node = connection.get_node(PortType.output)
    out_port_index = connection.get_port_index(PortType.output)
    line_style = Qt.SolidLine
    if out_node and hasattr(out_node.model, '_port_config'):
        config = out_node.model._port_config.get(PortType.output, {}).get(out_port_index, {})
        style_name = config.get('line_style', 'solid')
        if style_name == 'dashed': line_style = Qt.DashLine
        elif style_name == 'dotted': line_style = Qt.DotLine

    normal_color = style.get_normal_color()
    if style.use_data_defined_colors:
        normal_color = style.get_normal_color(connection.data_type(PortType.output).id)
    
    geom = connection.geometry
    p = QPen(normal_color)
    p.setWidthF(style.line_width)
    p.setStyle(line_style)
    
    if connection.graphics_object.isSelected():
        p.setColor(style.selected_color)
        
    painter.setPen(p)
    painter.setBrush(Qt.NoBrush)
    
    # Cubic path
    source, sink = geom.source, geom.sink
    c1, c2 = geom.points_c1_c2()
    path = QPolygonF() # Simplified for direct line segments if needed, but let's use QPainterPath
    from qtpy.QtGui import QPainterPath
    cubic = QPainterPath(source)
    cubic.cubicTo(c1, c2, sink)
    painter.drawPath(cubic)

ConnectionPainter.draw_normal_line = staticmethod(_patched_draw_normal_line)

_original_paint = NodePainter.paint

def _patched_paint(painter, node, scene, node_style, connection_style):
    model = node.model
    geom = node.geometry
    if model.name == "GroupNode":
        state = node.state
        
        width, height = geom.size.width(), geom.size.height()
        rect = QRectF(0, 0, width, height)
        
        # Slightly transparent background so it looks like a colored zone
        painter.setBrush(QColor(200, 200, 200, 15))
        
        # Border style
        line_style = Qt.DashLine if getattr(model, '_border_style', 'solid') == 'dashed' else Qt.SolidLine
        
        pen = QPen(QColor("#a0a0a0")) # Lighter border
        pen.setWidth(2)
        pen.setStyle(line_style)
        
        if node.graphics_object.isSelected():
            pen.setColor(QColor("#f39c12")) # Highlight when selected
            pen.setWidth(3)

        
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 10.0, 10.0)
        
        # Caption
        painter.setPen(QColor("#dddddd"))
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(10, 5, width - 20, 20), Qt.AlignLeft | Qt.AlignVCenter, getattr(model, '_name', 'Frame'))
        
        NodePainter.draw_resize_rect(painter, geom, model)
        return

    if model.name == "DiamondNode":
        width, height = geom.size.width(), geom.size.height()
        
        # Diamond Polygon
        poly = QPolygonF([
            QPointF(width/2, 0),      # Top
            QPointF(width, height/2), # Right
            QPointF(width/2, height), # Bottom
            QPointF(0, height/2)      # Left
        ])
        
        painter.setBrush(QColor(45, 45, 45))
        pen = QPen(QColor("#dddddd"))
        pen.setWidth(2)
        if node.graphics_object.isSelected():
            pen.setColor(QColor("#f39c12"))
            pen.setWidth(3)
        painter.setPen(pen)
        painter.drawPolygon(poly)
        
        # Caption
        painter.setPen(QColor("#dddddd"))
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(10, 10, width - 20, height - 20), Qt.AlignCenter, getattr(model, '_name', 'Decision'))
        
        # Draw connection points
        NodePainter.draw_connection_points(painter, geom, node.state, model, scene, node_style, connection_style)
        NodePainter.draw_filled_connection_points(painter, geom, node.state, model, node_style, connection_style)
        return

    if model.name == "CircleNode":
        width, height = geom.size.width(), geom.size.height()
        rect = QRectF(0, 0, width, height)
        
        painter.setBrush(QColor(45, 45, 45))
        pen = QPen(QColor("#dddddd"))
        pen.setWidth(2)
        if node.graphics_object.isSelected():
            pen.setColor(QColor("#f39c12"))
            pen.setWidth(3)
        painter.setPen(pen)
        painter.drawEllipse(rect)
        
        # Caption
        painter.setPen(QColor("#dddddd"))
        painter.drawText(rect, Qt.AlignCenter, getattr(model, '_name', 'Start'))
        
        # Draw connection points
        NodePainter.draw_connection_points(painter, geom, node.state, model, scene, node_style, connection_style)
        NodePainter.draw_filled_connection_points(painter, geom, node.state, model, node_style, connection_style)
        return

    _original_paint(painter, node, scene, node_style, connection_style)

NodePainter.paint = staticmethod(_patched_paint)

# --- Basic Node Models ---

class GroupNodeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

class GroupNodeModel(NodeDataModel):
    name = "GroupNode"
    caption = "Group / Frame"
    
    def __init__(self, **kwargs):
        style = kwargs.get('style')
        parent = kwargs.get('parent')
        NodeDataModel.__init__(self, style=style, parent=parent)
        self._border_style = 'solid'
        self._name = "Frame"
        self._widget = GroupNodeWidget()
        self._widget.setStyleSheet("background: transparent;")
        self._widget.setMinimumSize(300, 300)

    def embedded_widget(self):
        return self._widget
    
    def resizable(self):
        return True

    caption_visible = False
    port_caption_visible = False
        
    num_ports = { PortType.input: 0, PortType.output: 0 }
    data_type = { PortType.input: {}, PortType.output: {} }
    
    def save(self) -> dict:
        return {
            'border_style': self._border_style, 
            'name': self._name,
            'w': self._widget.width(),
            'h': self._widget.height()
        }

    def restore(self, state: dict):
        self._border_style = state.get('border_style', 'solid')
        self._name = state.get('name', 'Frame')
        w = state.get('w', 300)
        h = state.get('h', 300)
        self._widget.setMinimumSize(w, h)
        self._widget.resize(w, h)

class DiamondNodeModel(NodeDataModel):
    name = "DiamondNode"
    caption = "Decision (Diamond)"
    
    def __init__(self, **kwargs):
        style = kwargs.get('style')
        parent = kwargs.get('parent')
        NodeDataModel.__init__(self, style=style, parent=parent)
        self._name = "Is it correct?"
        self._widget = QWidget()
        self._widget.setStyleSheet("background: transparent;")
        self._widget.resize(80, 50)
        self._widget.setMinimumSize(40, 30)

    def embedded_widget(self): return self._widget
    def resizable(self): return True
    caption_visible = False
    port_caption_visible = True
    num_ports = { PortType.input: 2, PortType.output: 2 }
    data_type = {
        PortType.input: {0: NodeDataType(id="Any", name=""), 1: NodeDataType(id="Any", name="")},
        PortType.output: {0: NodeDataType(id="Any", name=""), 1: NodeDataType(id="Any", name="")}
    }
    
    def save(self) -> dict:
        return {
            'name': self._name,
            'w': self._widget.width(),
            'h': self._widget.height()
        }
    def restore(self, state: dict):
        self._name = state.get('name', "Is it correct?")
        w = state.get('w', 80)
        h = state.get('h', 50)
        self._widget.resize(w, h)

class CircleNodeModel(NodeDataModel):
    name = "CircleNode"
    caption = "Start / End"
    
    def __init__(self, **kwargs):
        style = kwargs.get('style')
        parent = kwargs.get('parent')
        NodeDataModel.__init__(self, style=style, parent=parent)
        self._name = "Start"
        self._widget = QWidget()
        self._widget.setStyleSheet("background: transparent;")
        self._widget.resize(60, 30)
        self._widget.setMinimumSize(40, 20)

    def embedded_widget(self): return self._widget
    def resizable(self): return True
    caption_visible = False
    port_caption_visible = True
    num_ports = { PortType.input: 1, PortType.output: 1 }
    data_type = {
        PortType.input: {0: NodeDataType(id="Any", name="")},
        PortType.output: {0: NodeDataType(id="Any", name="")}
    }
    
    def save(self) -> dict:
        return {
            'name': self._name,
            'w': self._widget.width(),
            'h': self._widget.height()
        }
    def restore(self, state: dict):
        self._name = state.get('name', "Start")
        w = state.get('w', 60)
        h = state.get('h', 30)
        self._widget.resize(w, h)

class TextNodeModel(NodeDataModel):
    name = "TextNode"
    caption = "Text Block"
    
    def __init__(self, **kwargs):
        style = kwargs.get('style')
        parent = kwargs.get('parent')
        NodeDataModel.__init__(self, style=style, parent=parent)
        self._text = "Text node"
        self._widget = QLineEdit(self._text)
        self._widget.textChanged.connect(self.on_text_changed)
        self._port_config = {PortType.input: {}, PortType.output: {}}

    def on_text_changed(self, text):
        self._text = text
        
    def embedded_widget(self):
        return self._widget
    
    caption_visible = True
    port_caption_visible = True
        
    num_ports = {
        PortType.input: 1,
        PortType.output: 1,
    }
    
    data_type = {
        PortType.input: {0: NodeDataType(id="Any", name="In")},
        PortType.output: {0: NodeDataType(id="Any", name="Out")},
    }
        
    def save(self) -> dict:
        doc = {
            'text': self._text
        }
        # Serialize _port_config
        serializable_config = {}
        for pt, configs in self._port_config.items():
            serializable_config[str(pt)] = configs
        doc['port_config'] = serializable_config
        return doc

    def restore(self, state: dict):
        self._text = state.get('text', "")
        self._widget.setText(self._text)
        
        config = state.get('port_config', {})
        self._port_config = {PortType.input: {}, PortType.output: {}}
        for pt_str, configs in config.items():
            pt = PortType.input if "input" in pt_str else PortType.output
            # Ensure indexes are integers
            self._port_config[pt] = {int(k): v for k, v in configs.items()}

    port_in_connection_policy = ConnectionPolicy.many
    port_out_connection_policy = ConnectionPolicy.many


class DatabaseNodeModel(NodeDataModel):
    name = "DatabaseNode"
    caption = "Database"
    
    def __init__(self, **kwargs):
        style = kwargs.get('style')
        parent = kwargs.get('parent')
        NodeDataModel.__init__(self, style=style, parent=parent)
        self._table_name = "Database"
        self._widget = QLineEdit(self._table_name)
        self._widget.setStyleSheet("background: #333; color: #fff; border: 1px solid #555; padding: 2px;")
        self._widget.textChanged.connect(self.on_text_changed)
        self._port_config = {PortType.input: {}, PortType.output: {}}

    def on_text_changed(self, text):
        self._table_name = text

    def embedded_widget(self):
        return self._widget

    caption_visible = True
    port_caption_visible = True
        
    num_ports = {
        PortType.input: 2,
        PortType.output: 2,
    }
    
    data_type = {
        PortType.input: {
            0: NodeDataType(id="Any", name="In 0"),
            1: NodeDataType(id="Any", name="In 1")
        },
        PortType.output: {
            0: NodeDataType(id="Any", name="Out 0"),
            1: NodeDataType(id="Any", name="Out 1")
        },
    }

    def save(self) -> dict:
        doc = {
            'table_name': self._table_name
        }
        serializable_config = {}
        for pt, configs in self._port_config.items():
            serializable_config[str(pt)] = configs
        doc['port_config'] = serializable_config
        return doc

    def restore(self, state: dict):
        self._table_name = state.get('table_name', "Database")
        self._widget.setText(self._table_name)
        
        config = state.get('port_config', {})
        self._port_config = {PortType.input: {}, PortType.output: {}}
        for pt_str, configs in config.items():
            pt = PortType.input if "input" in pt_str else PortType.output
            self._port_config[pt] = {int(k): v for k, v in configs.items()}

    port_in_connection_policy = ConnectionPolicy.many
    port_out_connection_policy = ConnectionPolicy.many


class DatabaseTableWidget(QWidget):
    def __init__(self, table_name="Table", columns=None, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(2)

        # Table Name
        self.name_edit = QLineEdit(table_name)
        self.name_edit.setStyleSheet("font-weight: bold; background: #333; color: white;")
        self.layout.addWidget(self.name_edit)

        # Columns Label
        self.layout.addWidget(QLabel("Columns:"))
        
        # Columns Container
        self.cols_container = QWidget()
        self.cols_layout = QVBoxLayout(self.cols_container)
        self.cols_layout.setContentsMargins(0, 0, 0, 0)
        self.cols_layout.setSpacing(2)
        self.layout.addWidget(self.cols_container)

        self.columns_edits = []
        if columns:
            for col in columns:
                self.add_column_edit(col)
        else:
            self.add_column_edit("id")

        # Add Column Button
        self.add_btn = QPushButton("+ Column")
        self.add_btn.setStyleSheet("background: #444; color: #ddd; font-size: 10px;")
        self.add_btn.clicked.connect(lambda: self.add_column_edit(""))
        self.layout.addWidget(self.add_btn)

    def add_column_edit(self, text):
        edit = QLineEdit(text)
        edit.setPlaceholderText("column_name")
        edit.setStyleSheet("background: #222; color: #bbb; border: 1px solid #444;")
        self.cols_layout.addWidget(edit)
        self.columns_edits.append(edit)
        # Inform the node that the size might have changed
        self.parent().model.embedded_widget_size_updated.emit() if self.parent() and hasattr(self.parent(), 'model') else None

    def get_columns(self):
        return [e.text() for e in self.columns_edits if e.text().strip()]

    def get_table_name(self):
        return self.name_edit.text()


class DatabaseTableNodeModel(NodeDataModel):
    name = "DatabaseTableNode"
    caption = "DB Table"
    
    def __init__(self, **kwargs):
        style = kwargs.get('style')
        parent = kwargs.get('parent')
        NodeDataModel.__init__(self, style=style, parent=parent)
        self._columns = ["id", "name", "created_at"]
        self._table_name = "NewTable"
        self._widget = DatabaseTableWidget(self._table_name, self._columns)
        self._widget.model = self
        self._port_config = {PortType.input: {}, PortType.output: {}}

    def embedded_widget(self):
        return self._widget

    def resizable(self):
        return True

    caption_visible = True
    port_caption_visible = True
        
    num_ports = {
        PortType.input: 1,
        PortType.output: 1,
    }
    
    data_type = {
        PortType.input: {0: NodeDataType(id="Any", name="In")},
        PortType.output: {0: NodeDataType(id="Any", name="Out")},
    }

    def save(self) -> dict:
        doc = {
            'table_name': self._widget.get_table_name(),
            'columns': self._widget.get_columns()
        }
        serializable_config = {}
        for pt, configs in self._port_config.items():
            serializable_config[str(pt)] = configs
        doc['port_config'] = serializable_config
        return doc

    def restore(self, state: dict):
        self._table_name = state.get('table_name', "NewTable")
        self._columns = state.get('columns', ["id"])
        self._widget = DatabaseTableWidget(self._table_name, self._columns)
        self._widget.model = self
        
        config = state.get('port_config', {})
        self._port_config = {PortType.input: {}, PortType.output: {}}
        for pt_str, configs in config.items():
            pt = PortType.input if "input" in pt_str else PortType.output
            self._port_config[pt] = {int(k): v for k, v in configs.items()}

    port_in_connection_policy = ConnectionPolicy.many
    port_out_connection_policy = ConnectionPolicy.many


class ArchitectureNodeWidget(QWidget):
    _icon_map = None
    _icon_names = None

    @classmethod
    def load_icons(cls):
        if cls._icon_map is not None:
            return
        cls._icon_map = {
            "bucket": "s3.png",
            "api": "api_gateway.png",
            "gateway": "api_gateway.png",
            "pc": "client.png",
            "computer": "client.png"
        }
        cls._icon_names = ["Bucket", "API Gateway", "Gateway", "PC", "Computer"]
        
        icons_dir = os.path.join("resources", "icons")
        if os.path.exists(icons_dir):
            for file in os.listdir(icons_dir):
                if file.endswith(".png"):
                    base_name = file[:-4]
                    formatted_name = base_name.replace("_", " ").title()
                    # Priority to exact file names
                    if base_name.lower() not in cls._icon_map:
                        cls._icon_map[base_name.lower()] = file
                    if formatted_name not in cls._icon_names:
                        cls._icon_names.append(formatted_name)

    def __init__(self, name="Client", parent=None):
        super().__init__(parent)
        self.load_icons()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(40, 40)
        self.image_label.setStyleSheet("background: transparent;")
        
        self.name_edit = QLineEdit(name)
        self.name_edit.setAlignment(Qt.AlignCenter)
        self.name_edit.setStyleSheet("background: rgba(0,0,0,80); color: white; border: none; font-weight: bold; font-size: 11px;")
        self.name_edit.textChanged.connect(self.update_icon)
        
        self.completer = QCompleter(self._icon_names, self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.name_edit.setCompleter(self.completer)
        
        self.layout.addWidget(self.image_label)
        self.layout.addWidget(self.name_edit)
        
        # Set a fixed, compact size for the icon node
        self.setFixedSize(100, 80)
        
        self.update_icon(name)

    def update_icon(self, name):
        name_lower = name.lower()
        
        icon_file = "client.png" # Default
        for key, file in self._icon_map.items():
            if key in name_lower:
                icon_file = file
                break
        
        icon_path = os.path.join("resources", "icons", icon_file)
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            # Use a slightly smaller target for the scaling to fit nicely in the fixed size
            self.image_label.setPixmap(pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.image_label.setText("?")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_icon(self.name_edit.text())


class ArchitectureNodeModel(NodeDataModel):
    name = "ArchitectureNode"
    caption = "Arch Component"
    
    def __init__(self, **kwargs):
        style = kwargs.get('style')
        parent = kwargs.get('parent')
        NodeDataModel.__init__(self, style=style, parent=parent)
        self._name = "Client"
        self._widget = ArchitectureNodeWidget(self._name)
        self._widget.model = self
        self._port_config = {PortType.input: {}, PortType.output: {}}

    def embedded_widget(self):
        return self._widget

    def resizable(self):
        return False

    caption_visible = False
    port_caption_visible = True
        
    num_ports = {
        PortType.input: 1,
        PortType.output: 1,
    }
    
    data_type = {
        PortType.input: {0: NodeDataType(id="Any", name="In")},
        PortType.output: {0: NodeDataType(id="Any", name="Out")},
    }

    def save(self) -> dict:
        doc = {
            'name': self._widget.name_edit.text()
        }
        serializable_config = {}
        for pt, configs in self._port_config.items():
            serializable_config[str(pt)] = configs
        doc['port_config'] = serializable_config
        return doc

    def restore(self, state: dict):
        self._name = state.get('name', "Client")
        self._widget.name_edit.setText(self._name)
        
        config = state.get('port_config', {})
        self._port_config = {PortType.input: {}, PortType.output: {}}
        for pt_str, configs in config.items():
            pt = PortType.input if "input" in pt_str else PortType.output
            self._port_config[pt] = {int(k): v for k, v in configs.items()}

    port_in_connection_policy = ConnectionPolicy.many
    port_out_connection_policy = ConnectionPolicy.many



# --- Main Tab Widget ---

class NewDiagramDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Diagram")
        self.setFixedWidth(300)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Diagram Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter diagram name...")
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("Diagram Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Advanced Architecture", "Basic Flowchart"])
        layout.addWidget(self.type_combo)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def get_data(self):
        return self.name_input.text(), self.type_combo.currentText()


class ProjectDiagramTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setObjectName("ProjectDiagramTab")
        self.current_diagram_file = None
        self.project_id = None
        self.diagrams_dir = ""

        if not HAS_NODE_EDITOR:
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel("Error: qtpynodeeditor is not installed. Please run `poetry add qtpynodeeditor`"))
            return

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(5)

        # Confirmation Widget (Inline - Top Level)
        from PySide6.QtWidgets import QSizePolicy
        self.confirmation_widget = QWidget()
        self.confirmation_widget.setVisible(False)
        self.confirmation_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        
        self.confirm_layout = QVBoxLayout(self.confirmation_widget)
        self.confirm_layout.setContentsMargins(0, 0, 0, 10)
        self.confirm_layout.setSpacing(5)

        self.confirm_label = QLabel("Delete this Diagram?")
        self.confirm_label.setStyleSheet("color: #ff4d4d; font-weight: bold; font-size: 14px;")
        self.confirm_layout.addWidget(self.confirm_label)

        self.confirm_btns_layout = QHBoxLayout()
        self.confirm_yes_btn = QPushButton("Yes, Delete")
        self.confirm_yes_btn.setStyleSheet("background-color: #ff4d4d; color: white; padding: 5px 15px;")
        self.confirm_yes_btn.clicked.connect(self.perform_delete)
        
        self.confirm_no_btn = QPushButton("Cancel")
        self.confirm_no_btn.clicked.connect(self.cancel_delete)
        
        self.confirm_btns_layout.addWidget(self.confirm_yes_btn)
        self.confirm_btns_layout.addWidget(self.confirm_no_btn)
        self.confirm_btns_layout.addStretch()
        self.confirm_layout.addLayout(self.confirm_btns_layout)

        self.main_layout.addWidget(self.confirmation_widget)

        # Explorer section (Left)
        self.explorer_group = QWidget()
        self.explorer_layout = QVBoxLayout(self.explorer_group)
        self.explorer_layout.setContentsMargins(0, 0, 0, 0)
        
        self.diagrams_list = QListWidget()
        self.diagrams_list.setStyleSheet("QListWidget QLineEdit { padding: 0px; margin: 0px; height: 26px; }")
        self.diagrams_list.itemClicked.connect(self.open_selected_diagram)
        self.diagrams_list.itemChanged.connect(self.on_diagram_renamed)
        self.diagrams_list.installEventFilter(self)
        self.explorer_layout.addWidget(self.diagrams_list)

        # Bottom buttons for explorer
        self.bottom_buttons_layout = QVBoxLayout()
        self.bottom_buttons_layout.setSpacing(5)
        
        self.new_btn = QPushButton("📄 New")
        self.new_btn.setFixedHeight(32)
        self.new_btn.clicked.connect(self.create_new_diagram)
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.setFixedHeight(32)
        self.delete_btn.setStyleSheet("color: #ff4d4d;")
        self.delete_btn.clicked.connect(self.delete_selected_diagram)
        
        self.bottom_buttons_layout.addWidget(self.new_btn)
        self.bottom_buttons_layout.addWidget(self.delete_btn)
        self.explorer_layout.addLayout(self.bottom_buttons_layout)
        
        # Editor section (Right)
        self.editor_group = QWidget()
        self.editor_layout = QVBoxLayout(self.editor_group)
        
        self.toolbar = QHBoxLayout()
        self.center_btn = QPushButton("🎯 Center View")
        self.center_btn.setFixedHeight(32)
        self.center_btn.clicked.connect(self.center_view)
        
        self.clear_btn = QPushButton("🧹 Clear Scene")
        self.clear_btn.clicked.connect(self.clear_scene)
        
        self.export_img_btn = QPushButton("🖼️ Export Image")
        self.export_img_btn.setFixedHeight(32)
        self.export_img_btn.clicked.connect(self.export_diagram_as_image)
        
        self.toolbar.addWidget(self.center_btn)
        self.toolbar.addSpacing(10)
        self.toolbar.addWidget(self.export_img_btn)
        self.toolbar.addSpacing(10)
        self.toolbar.addWidget(self.clear_btn)
        self.toolbar.addStretch()
        self.editor_layout.addLayout(self.toolbar)

        # Initialize Node Editor
        self.registry = self.register_models()
        self.scene = FlowScene(registry=self.registry)
        self.scene.node_context_menu.connect(self.show_node_context_menu)
        self.scene.node_created.connect(self.on_node_created)
        self.view = FlowView(self.scene)
        self.editor_layout.addWidget(self.view)

        # Splitter
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.explorer_group)
        self.splitter.addWidget(self.editor_group)
        self.splitter.setSizes([150, 650])
        self.main_layout.addWidget(self.splitter, 1)
        
        self.setEnabled(False)

    def register_models(self):
        registry = DataModelRegistry()
        registry.register_model(GroupNodeModel, "Groups")
        registry.register_model(DiamondNodeModel, "Flowchart")
        registry.register_model(CircleNodeModel, "Flowchart")
        registry.register_model(TextNodeModel, "Shapes")
        registry.register_model(DatabaseNodeModel, "Architecture")
        registry.register_model(DatabaseTableNodeModel, "Database")
        registry.register_model(ArchitectureNodeModel, "Architecture")
        return registry

    def register_basic_models(self):
        registry = DataModelRegistry()
        registry.register_model(GroupNodeModel, "Groups")
        registry.register_model(DiamondNodeModel, "Flowchart")
        registry.register_model(CircleNodeModel, "Flowchart")
        registry.register_model(TextNodeModel, "Flowchart")
        return registry

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            if self.diagrams_list.hasFocus() and self.diagrams_list.currentItem():
                self.delete_selected_diagram()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def set_project_id(self, project_id):
        self.project_id = str(project_id)
        self.diagrams_list.clear()
        self.clear_scene()
        self.current_diagram_file = None
        
        if project_id:
            self.setEnabled(True)
            self.diagrams_dir = os.path.join(self.main_window.storage_dir, self.project_id, "diagrams")
            if not os.path.exists(self.diagrams_dir):
                try: os.makedirs(self.diagrams_dir)
                except OSError: pass
            self.load_diagrams_from_dir()
        else:
            self.setEnabled(False)

    def load_diagrams_from_dir(self):
        self.diagrams_list.clear()
        if os.path.exists(self.diagrams_dir):
            files = [f for f in os.listdir(self.diagrams_dir) if f.endswith('.json')]
            for f in files:
                item = QListWidgetItem(f"📐 {f}")
                item.setData(Qt.UserRole, os.path.join(self.diagrams_dir, f))
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                item.setSizeHint(QSize(0, 30))
                self.diagrams_list.addItem(item)

    @Slot()
    def create_new_diagram(self):
        dialog = NewDiagramDialog(self)
        if dialog.exec():
            name, diagram_type = dialog.get_data()
            if name:
                if not name.lower().endswith(".json"): name += ".json"
                path = os.path.join(self.diagrams_dir, name)
                try:
                    # Create empty scene json
                    empty_scene = {"type": diagram_type, "nodes": [], "connections": []}
                            
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(json.dumps(empty_scene, indent=4))
                    
                    self.load_diagrams_from_dir()
                    for i in range(self.diagrams_list.count()):
                        item = self.diagrams_list.item(i)
                        if item.data(Qt.UserRole) == path:
                            self.diagrams_list.setCurrentItem(item)
                            self.open_selected_diagram(item)
                            break
                except Exception as e:
                    QMessageBox.critical(self, "Error", str(e))

    @Slot()
    def open_selected_diagram(self, item):
        self.current_diagram_file = item.data(Qt.UserRole)
        if os.path.exists(self.current_diagram_file):
            try:
                with open(self.current_diagram_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                diagram_type = data.get("type", "Advanced Architecture")
                
                # Load models based on diagram type
                if diagram_type == "Basic Flowchart":
                    self.registry = self.register_basic_models()
                else:
                    self.registry = self.register_models()
                
                # We update the scene to reflect only the allowed node models
                old_scene = self.scene
                self.scene = FlowScene(registry=self.registry)
                self.scene.node_context_menu.connect(self.show_node_context_menu)
                self.scene.node_created.connect(self.on_node_created)
                
                # Auto-save connections
                self.scene.node_deleted.connect(self.save_current_diagram)
                self.scene.connection_created.connect(self.save_current_diagram)
                self.scene.connection_deleted.connect(self.save_current_diagram)
                self.scene.node_moved.connect(self.save_current_diagram)
                
                self.view.setScene(self.scene)
                
                self.scene.__setstate__(data)
                for n in self.scene.nodes.values():
                    if n.model.name == "GroupNode":
                        n.graphics_object.setZValue(-10)
                
                self.center_btn.setVisible(True)
                self.clear_btn.setVisible(True)

            except Exception as e:
                import traceback; traceback.print_exc()
                QMessageBox.critical(self, "Error", f"Could not load diagram: {e}")

    @Slot()
    def save_current_diagram(self):
        if self.current_diagram_file:
            try:
                data = self.scene.__getstate__()
                with open(self.current_diagram_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save diagram: {e}")

    @Slot()
    def clear_scene(self):
        self.scene.clear_scene()

    def center_view(self):
        # Center scene at origin
        self.view.centerOn(0, 0)

    @Slot()
    def delete_selected_diagram(self):
        current_item = self.diagrams_list.currentItem()
        if not current_item: return
        
        self.to_delete_path = current_item.data(Qt.UserRole)
        name = current_item.text().replace("📐 ", "")
        
        self.confirm_label.setText(f"Delete Diagram '{name}'?")
        self.confirmation_widget.setVisible(True)
        self.new_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)

    @Slot()
    def export_diagram_as_image(self):
        if not self.scene: return
        
        # Get the area occupied by all nodes
        items_rect = self.scene.itemsBoundingRect()
        if items_rect.isEmpty():
            QMessageBox.information(self, "Export", "Diagram is empty.")
            return
            
        # Add some padding (20px)
        items_rect.adjust(-20, -20, 20, 20)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Diagram as Image", "", 
            "PNG Files (*.png);;All Files (*)"
        )
        
        if not file_path:
            return
            
        if not file_path.lower().endswith(".png"):
            file_path += ".png"
            
        # Create image with transparent background
        image = QImage(items_rect.size().toSize(), QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Render the scene content within items_rect into the entire image rect
        self.scene.render(painter, QRectF(image.rect()), items_rect)
        painter.end()
        
        if image.save(file_path):
            QMessageBox.information(self, "Export", f"Diagram exported successfully to:\n{file_path}")
        else:
            QMessageBox.critical(self, "Error", "Could not save the image. Check permissions.")

    @Slot()
    def perform_delete(self):
        if hasattr(self, 'to_delete_path') and self.to_delete_path:
            try:
                if os.path.exists(self.to_delete_path):
                    os.remove(self.to_delete_path)
                
                if self.current_diagram_file == self.to_delete_path:
                    self.current_diagram_file = None
                    self.clear_scene()
                
                self.load_diagrams_from_dir()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not delete: {str(e)}")
                return
        self.cancel_delete()

    def eventFilter(self, source, event):
        if source is self.diagrams_list and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Delete:
                self.delete_selected_diagram()
                return True
        return super().eventFilter(source, event)

    @Slot()
    def cancel_delete(self):
        self.to_delete_path = None
        self.confirmation_widget.setVisible(False)
        self.new_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        self.diagrams_list.setFocus()

    @Slot(object)
    def on_node_created(self, node):
        if node.model.name == "GroupNode":
            node.graphics_object.setZValue(-10)
        self.save_current_diagram()

    def set_group_border(self, model, style, node):
        model._border_style = style
        node.graphics_object.update()
        self.save_current_diagram()

    def rename_generic_node(self, model, node):
        text, ok = QInputDialog.getText(self, "Rename Node", "New text:", QLineEdit.Normal, model._name)
        if ok and text:
            model._name = text
            node.graphics_object.update()
            self.save_current_diagram()

    def show_node_context_menu(self, node, pos, screen_pos):
        menu = QMenu(self)
        model = node.model
        
        if model.name in ["DiamondNode", "CircleNode"]:
            rename_act = menu.addAction("Edit Text")
            rename_act.triggered.connect(lambda: self.rename_generic_node(model, node))
            menu.addSeparator()
            delete_action = menu.addAction("Delete Node")
            delete_action.triggered.connect(lambda: self.scene.remove_node(node))
            menu.exec(screen_pos)
            return

        if model.name == "GroupNode":
            border_menu = menu.addMenu("Border Style")
            solid_act = border_menu.addAction("Solid")
            solid_act.setCheckable(True)
            solid_act.setChecked(model._border_style == 'solid')
            solid_act.triggered.connect(lambda: self.set_group_border(model, 'solid', node))
            
            dashed_act = border_menu.addAction("Dashed")
            dashed_act.setCheckable(True)
            dashed_act.setChecked(model._border_style == 'dashed')
            dashed_act.triggered.connect(lambda: self.set_group_border(model, 'dashed', node))
            
            rename_act = menu.addAction("Rename Group")
            rename_act.triggered.connect(lambda: self.rename_group(model, node))
            
            menu.addSeparator()
            delete_action = menu.addAction("Delete Group")
            delete_action.triggered.connect(lambda: self.scene.remove_node(node))
            menu.exec(screen_pos)
            return
        
        # Ports Customization
        for pt_name, pt in [("Input", PortType.input), ("Output", PortType.output)]:
            pt_menu = menu.addMenu(f"{pt_name} Ports")
            num = model.num_ports[pt]
            for i in range(num):
                port_menu = pt_menu.addMenu(f"Port {i}")
                
                # Shape action group
                shape_menu = port_menu.addMenu("Shape")
                for s in ['circle', 'arrow', 'many']:
                    checked = model._port_config[pt].get(i, {}).get('shape', 'circle') == s
                    act = shape_menu.addAction(s.capitalize())
                    act.setCheckable(True)
                    act.setChecked(checked)
                    act.triggered.connect(lambda chk=False, p=pt, idx=i, val=s: self.set_port_config(model, p, idx, 'shape', val))
                
                # Line style (only for output)
                if pt == PortType.output:
                    line_menu = port_menu.addMenu("Line Style")
                    for ls in ['solid', 'dashed', 'dotted']:
                        checked = model._port_config[pt].get(i, {}).get('line_style', 'solid') == ls
                        act = line_menu.addAction(ls.capitalize())
                        act.setCheckable(True)
                        act.setChecked(checked)
                        act.triggered.connect(lambda chk=False, p=pt, idx=i, val=ls: self.set_port_config(model, p, idx, 'line_style', val))

        menu.addSeparator()
        delete_action = menu.addAction("Delete Node")
        delete_action.triggered.connect(lambda: self.scene.delete_node(node))
        
        menu.exec(screen_pos)

    def set_port_config(self, model, port_type, index, key, value):
        if index not in model._port_config[port_type]:
            model._port_config[port_type][index] = {}
        model._port_config[port_type][index][key] = value
        # Trigger redraw
        self.scene.update()
        for conn in self.scene.connections:
             conn.graphics_object.update()
        self.save_current_diagram()

    @Slot(QListWidgetItem)
    def on_diagram_renamed(self, item):
        old_path = item.data(Qt.UserRole)
        if not old_path or not os.path.exists(old_path):
            return

        new_name = item.text()
        if new_name.startswith("📐 "):
            new_name = new_name[2:]
        else:
            self.diagrams_list.blockSignals(True)
            item.setText(f"📐 {new_name}")
            self.diagrams_list.blockSignals(False)
            
        old_dir = os.path.dirname(old_path)
        new_path = os.path.join(old_dir, new_name)

        if old_path != new_path:
            # force .json extension
            if not new_path.endswith('.json'):
                new_path += '.json'
                
            try:
                os.rename(old_path, new_path)
                item.setData(Qt.UserRole, new_path)
                if self.current_diagram_file == old_path:
                    self.current_diagram_file = new_path
                    
                # Fix up name to include .json if it didn't
                final_name = os.path.basename(new_path)
                self.diagrams_list.blockSignals(True)
                item.setText(f"📐 {final_name}")
                self.diagrams_list.blockSignals(False)
                
            except Exception as e:
                self.diagrams_list.blockSignals(True)
                item.setText(f"📐 {os.path.basename(old_path)}")
                self.diagrams_list.blockSignals(False)
                QMessageBox.critical(self, "Error", f"Could not rename diagram: {e}")
