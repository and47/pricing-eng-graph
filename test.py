"" 

class Component:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent

    def get_size(self):
        pass

class File(Component):
    def __init__(self, name, size=0, parent=None):
        super().__init__(name, parent)
        self.size = size

    def get_size(self):
        return self.size

    def update_size(self, new_size):
        old_size = self.size
        self.size = new_size
        size_difference = new_size - old_size
        print(f"{self.name} size updated from {old_size} to {new_size}")
        if self.parent:
            self.parent.update_size(size_difference)

class Folder(Component):
    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.children = []
        self._size = 0  # Track the cumulative size

    def add_child(self, component):
        component.parent = self
        self.children.append(component)
        self._size += component.get_size()

    def get_size(self):
        return self._size

    def update_size(self, size_difference):
        self._size += size_difference
        print(f"{self.name} size: {self.get_size()}")
        if self.parent:
            self.parent.update_size(size_difference)
            
            
            
            
            
            
            
            
            
            
            
            
########## multiple parents

class Component:
    def __init__(self, name):
        self.name = name
        self.parents = []  # Now a list to support multiple parents

    def add_parent(self, parent):
        if parent not in self.parents:
            self.parents.append(parent)

    def remove_parent(self, parent):
        if parent in self.parents:
            self.parents.remove(parent)

class File(Component):
    def __init__(self, name, size=0):
        super().__init__(name)
        self.size = size

    def update_size(self, new_size):
        old_size = self.size
        self.size = new_size
        size_difference = new_size - old_size
        print(f"{self.name} size updated from {old_size} to {new_size}")
        for parent in self.parents:
            parent.update_size(size_difference)

class Folder(Component):
    def __init__(self, name):
        super().__init__(name)
        self.children = []
        self.size = 0

    def add_child(self, component):
        if component not in self.children:
            component.add_parent(self)
            self.children.append(component)
            self.size += component.size

    def update_size(self, size_difference):
        self.size += size_difference
        print(f"{self.name} size: {self.size}")
        for parent in self.parents:
            parent.update_size(size_difference)


            