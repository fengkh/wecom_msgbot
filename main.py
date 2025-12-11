from rabbitMQ import main
from ui_controller import init_component_location

if __name__ == '__main__':
    components = init_component_location()
    main(components)
