import hashlib
import logging
import re
import uuid
from datetime import datetime, UTC
import time
import os

from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Text, event, func, Index
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, validates, joinedload

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("module_2/app.log"),
        logging.StreamHandler()
    ]
)
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
logger = logging.getLogger(__name__)


# Create base class with audit columns
class BaseModel(object):
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    created_by = Column(String(50))
    updated_by = Column(String(50))


Base = declarative_base(cls=BaseModel)


# Data validation functions
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValueError("Invalid email format")
    return email


def hash_password(password):
    # In production, use a proper password hashing library like bcrypt
    salt = uuid.uuid4().hex
    return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(128), nullable=False)

    # Relationship
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('ix_users_id', 'id'),
        Index('ix_users_username', 'username'),
        Index('ix_users_email', 'email')
    )

    @validates('email')
    def validate_email(self, key, address):
        return validate_email(address)

    @validates('username')
    def validate_username(self, key, username):
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")
        return username


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)

    # Relationship
    order_items = relationship("OrderItem", back_populates="product")

    # Indexes
    __table_args__ = (
        Index('ix_products_id', 'id'),
        Index('ix_products_name', 'name'),
        Index('ix_products_price', 'price')
    )

    @validates('price')
    def validate_price(self, key, price):
        if price <= 0:
            raise ValueError("Price must be greater than zero")
        return price

    @validates('stock')
    def validate_stock(self, key, stock):
        if stock < 0:
            raise ValueError("Stock cannot be negative")
        return stock


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    order_date = Column(DateTime, default=datetime.now(UTC))
    status = Column(String(50), default='pending')

    # Relationships
    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('ix_orders_id', 'id'),
        Index('ix_orders_user_id', 'user_id'),
        Index('ix_orders_status', 'status')
    )

    @validates('status')
    def validate_status(self, key, status):
        valid_statuses = ['pending', 'completed', 'cancelled']
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return status


class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")

    # Indexes
    __table_args__ = (
        Index('ix_order_items_id', 'id'),
        Index('ix_order_items_order_id', 'order_id'),
        Index('ix_order_items_product_id', 'product_id')
    )

    @validates('quantity')
    def validate_quantity(self, key, quantity):
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero")
        return quantity


# Event listener for auditing
@event.listens_for(BaseModel, 'before_insert')
def receive_before_insert(mapper, connection, target):
    if isinstance(target, BaseModel):
        target.created_at = datetime.now(UTC)
        target.updated_at = datetime.now(UTC)


@event.listens_for(BaseModel, 'before_update')
def receive_before_update(mapper, connection, target):
    if isinstance(target, BaseModel):
        target.updated_at = datetime.now(UTC)
        # Log the update
        logger.info(f"Updated {target.__class__.__name__} with ID {target.id} by {target.updated_by}")


@event.listens_for(BaseModel, 'before_delete')
def receive_before_delete(mapper, connection, target):
    if isinstance(target, BaseModel):
        # Log the deletion
        logger.info(f"Deleted {target.__class__.__name__} with ID {target.id} by {target.updated_by}")


def execute_with_retry(operation_name, operation_func, max_retries=3, retry_delay=1):
    """Execute database operation with automatic retry on connection errors"""
    retries = 0
    while True:
        try:
            return operation_func()
        except OperationalError as e:
            retries += 1
            if retries > max_retries:
                logger.error(f"Database connection error in {operation_name} after {retries} attempts: {str(e)}")
                raise

            logger.warning(f"Connection error in {operation_name}, retrying ({retries}/{max_retries}): {str(e)}")
            time.sleep(retry_delay)


def _handle_integrity_error(error, entity_type="record"):
    """Extract useful information from IntegrityError to provide better error messages"""
    error_msg = str(error).lower()

    if "unique constraint" in error_msg or "unique violation" in error_msg or "duplicate" in error_msg:
        # Extract field name from error message - implementation depends on database dialect
        if "username" in error_msg:
            return f"A {entity_type} with this username already exists"
        elif "email" in error_msg:
            return f"A {entity_type} with this email address already exists"
        else:
            return f"This {entity_type} already exists"

    return f"Database integrity error: {str(error)}"


class DatabaseManager:
    def __init__(self, engine):
        self.engine = engine
        self.Session = sessionmaker(bind=engine)

    def create_user(self, username, email, password, current_user="system"):
        """Create a new user with proper validation and error handling"""

        def _opertaion():
            session = self.Session()
            try:
                # Begin transaction
                user = User(
                    username=username,
                    email=email,
                    password_hash=hash_password(password),
                    created_by=current_user,
                    updated_by=current_user
                )
                session.add(user)
                session.commit()

                # Extract needed data before closing session
                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }

                logger.info(f"User created: {username}")
                return user_data

            except IntegrityError as e:
                session.rollback()
                error_msg = _handle_integrity_error(e, "user")
                logger.error(f"Integrity error creating user: {error_msg}")
                raise ValueError(error_msg)
            except ValueError as e:
                # Validation error
                session.rollback()
                logger.error(f"Validation error: {str(e)}")
                raise
            except SQLAlchemyError as e:
                # Database error
                session.rollback()
                logger.error(f"Database error creating user: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("create_user", _opertaion)

    def create_product(self, name, price, description=None, stock=0, current_user="system"):
        """Create a new product with validation"""

        def _operation():
            session = self.Session()
            try:
                product = Product(
                    name=name,
                    description=description,
                    price=price,
                    stock=stock,
                    created_by=current_user,
                    updated_by=current_user
                )
                session.add(product)
                session.commit()

                # Extract needed data before closing session
                product_data = {
                    'id': product.id,
                    'name': product.name,
                    'description': product.description,
                    'price': product.price,
                    'stock': product.stock
                }

                logger.info(f"Product created: {name}")
                return product_data
            except ValueError as e:
                session.rollback()
                logger.error(f"Validation error: {str(e)}")
                raise
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error creating product: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("create_product", _operation)

    def create_order(self, user_id, items, current_user="system"):
        """
        Create an order with multiple items in a single transaction

        Args:
            user_id: The ID of the user making the order
            items: List of dicts with product_id, quantity
            current_user: Username for audit trail
        """

        def _operation():
            session = self.Session()
            try:
                # Verify user exists
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    raise ValueError(f"User with ID {user_id} not found")

                # Create the order
                order = Order(
                    user_id=user_id,
                    status='pending',
                    created_by=current_user,
                    updated_by=current_user
                )
                session.add(order)
                session.flush()  # Flush to get the order ID without committing

                # Process each item
                for item_data in items:
                    product_id = item_data['product_id']
                    quantity = item_data['quantity']

                    # Verify product exists and has enough stock
                    product = session.query(Product).filter(Product.id == product_id).with_for_update().first()
                    if not product:
                        raise ValueError(f"Product with ID {product_id} not found")

                    if product.stock < quantity:
                        raise ValueError(f"Insufficient stock for product {product.name}")

                    # Update stock
                    product.stock -= quantity

                    # Create order item
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=product_id,
                        quantity=quantity,
                        price=product.price,  # Capture price at time of purchase
                        created_by=current_user,
                        updated_by=current_user
                    )
                    session.add(order_item)

                # Commit all changes in one transaction
                session.commit()

                # Extract order data before closing session
                # Extract order data before closing session
                order_data = {
                    'id': order.id,
                    'user_id': order.user_id,
                    'status': order.status,
                    'order_date': order.order_date
                }

                logger.info(f"Order created: {order.id} for user {user_id}")
                return order_data
            except Exception as e:
                session.rollback()
                logger.error(f"Error creating order: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("create_order", _operation)

    def get_user(self, user_id):
        """Get a user by ID with proper session management"""

        def _operation():
            session = self.Session()
            try:
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    logger.info(f"User with ID {user_id} not found")
                    return None

                # Load all needed data before closing session
                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'created_at': user.created_at,
                    'created_by': user.created_by,
                }

                logger.info(f"Retrieved user: {user.username}")
                return user_data
            except SQLAlchemyError as e:
                logger.error(f"Database error retrieving user: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("get_user", _operation)

    def get_product(self, product_id):
        """Get a product by ID"""

        def _operation():
            session = self.Session()
            try:
                product = session.query(Product).filter(Product.id == product_id).first()
                if not product:
                    logger.info(f"Product with ID {product_id} not found")
                    return None

                product_data = {
                    'id': product.id,
                    'name': product.name,
                    'description': product.description,
                    'price': product.price,
                    'stock': product.stock,
                    'created_at': product.created_at,
                    'created_by': product.created_by,
                }

                logger.info(f"Retrieved product: {product.name}")
                return product_data
            except SQLAlchemyError as e:
                logger.error(f"Database error retrieving product: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("get_product", _operation)

    def get_order_with_items(self, order_id):
        """Get an order with all its items using eager loading"""

        def _operation():
            session = self.Session()
            try:
                # Use eager loading to avoid subsequent queries
                order = session.query(Order).options(
                    joinedload(Order.order_items).joinedload(OrderItem.product)
                ).filter(Order.id == order_id).first()

                if not order:
                    logger.info(f"Order with ID {order_id} not found")
                    return None

                # Build a complete data structure including related entities
                order_data = {
                    'id': order.id,
                    'user_id': order.user_id,
                    'order_date': order.order_date,
                    'status': order.status,
                    'created_at': order.created_at,
                    'created_by': order.created_by,
                    'items': []
                }

                for item in order.order_items:
                    order_data['items'].append({
                        'id': item.id,
                        'product_id': item.product_id,
                        'product_name': item.product.name,
                        'quantity': item.quantity,
                        'price': item.price
                    })

                logger.info(f"Retrieved order: {order.id} with {len(order_data['items'])} items")
                return order_data
            except SQLAlchemyError as e:
                logger.error(f"Database error retrieving order: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("get_order_with_items", _operation)

    def list_users(self, page=1, page_size=10, search=None):
        """List users with pagination and optional search"""

        def _operation():
            session = self.Session()
            try:
                query = session.query(User)

                # Apply search filter if provided
                if search:
                    query = query.filter(User.username.like(f"%{search}%") |
                                         User.email.like(f"%{search}%"))

                # Get total count for pagination
                total_count = query.count()

                # Apply pagination
                users = query.limit(page_size).offset((page - 1) * page_size).all()

                # Convert to dictionaries before session closes
                result = {
                    'total': total_count,
                    'page': page,
                    'page_size': page_size,
                    'users': [{
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'created_at': user.created_at
                    } for user in users]
                }

                logger.info(f"Retrieved {len(users)} users (page {page})")
                return result
            except SQLAlchemyError as e:
                logger.error(f"Database error listing users: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("list_users", _operation)

    def list_products(self, page=1, page_size=10, min_price=None, max_price=None, search=None):
        """List products with filtering, pagination and optional search"""

        def _operation():
            session = self.Session()
            try:
                query = session.query(Product)

                # Apply filters
                if min_price is not None:
                    query = query.filter(Product.price >= min_price)
                if max_price is not None:
                    query = query.filter(Product.price <= max_price)
                if search:
                    query = query.filter(Product.name.like(f"%{search}%") |
                                         Product.description.like(f"%{search}%"))

                # Get total count for pagination
                total_count = query.count()

                # Apply pagination
                products = query.limit(page_size).offset((page - 1) * page_size).all()

                # Convert to dictionaries before session closes
                result = {
                    'total': total_count,
                    'page': page,
                    'page_size': page_size,
                    'products': [{
                        'id': product.id,
                        'name': product.name,
                        'description': product.description,
                        'price': product.price,
                        'stock': product.stock
                    } for product in products]
                }

                logger.info(f"Retrieved {len(products)} products (page {page})")
                return result
            except SQLAlchemyError as e:
                logger.error(f"Database error listing products: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("list_products", _operation)

    def get_user_orders(self, user_id, page=1, page_size=10):
        """Get all orders for a specific user with pagination"""

        def _operation():
            session = self.Session()
            try:
                # First verify user exists
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    raise ValueError(f"User with ID {user_id} not found")

                # Query orders with a count
                total_count = session.query(Order).filter(Order.user_id == user_id).count()

                # Get orders with items using eager loading
                orders = session.query(Order).options(
                    joinedload(Order.order_items)
                ).filter(Order.user_id == user_id).order_by(
                    Order.order_date.desc()
                ).limit(page_size).offset((page - 1) * page_size).all()

                # Process into dictionaries before session closes
                result = {
                    'total': total_count,
                    'page': page,
                    'page_size': page_size,
                    'orders': []
                }

                for order in orders:
                    order_dict = {
                        'id': order.id,
                        'order_date': order.order_date,
                        'status': order.status,
                        'items_count': len(order.order_items),
                        'total_amount': sum(item.price * item.quantity for item in order.order_items)
                    }
                    result['orders'].append(order_dict)

                logger.info(f"Retrieved {len(orders)} orders for user {user_id}")
                return result
            except ValueError as e:
                logger.error(str(e))
                raise
            except SQLAlchemyError as e:
                logger.error(f"Database error retrieving user orders: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("get_user_orders", _operation)

    def get_total_quantity_sold(self):
        """Get total quantity sold for each product"""

        def _operation():
            session = self.Session()
            try:
                # Use a join to get the total quantity sold for each product
                result = session.query(
                    Product.name,
                    func.sum(OrderItem.quantity).label('total_sold')
                ).join(OrderItem).group_by(Product.id).all()

                # Convert to dictionaries before session closes
                total_sold_data = [{
                    'product_name': row[0],
                    'total_quantity_sold': row[1]
                } for row in result]

                logger.info(f"Retrieved total quantity sold data")
                return total_sold_data
            except SQLAlchemyError as e:
                logger.error(f"Database error retrieving total quantity sold: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("get_total_quantity_sold", _operation)

    def update_user(self, user_id, data, current_user="system"):
        """Update a user with proper validation and transaction management"""

        def _operation():
            session = self.Session()
            try:
                # Retrieve user
                user = session.query(User).filter(User.id == user_id).first()
                if not user:
                    raise ValueError(f"User with ID {user_id} not found")

                # Update fields with validation
                if 'username' in data:
                    user.username = data['username']  # Validation happens in @validates
                if 'email' in data:
                    user.email = data['email']  # Validation happens in @validates
                if 'password' in data:
                    user.password_hash = hash_password(data['password'])

                # Track who updated
                user.updated_by = current_user

                # Commit changes
                session.commit()

                # Extract data before closing session
                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'created_at': user.created_at,
                    'updated_at': user.updated_at
                }

                logger.info(f"Updated user: {user.username} by {current_user}")
                return user_data

            except IntegrityError as e:
                session.rollback()
                error_msg = _handle_integrity_error(e, "user")
                logger.error(f"Integrity error updating user: {error_msg}")
                raise ValueError(error_msg)
            except ValueError as e:
                session.rollback()
                logger.error(f"Validation error: {str(e)}")
                raise
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error updating user: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("update_user", _operation)

    def update_product(self, product_id, data, current_user="system"):
        """Update a product with proper validation and transaction management"""

        def _operation():
            session = self.Session()
            try:
                # Retrieve product with lock for update
                product = session.query(Product).filter(Product.id == product_id).with_for_update().first()
                if not product:
                    raise ValueError(f"Product with ID {product_id} not found")

                # Update fields with validation
                if 'name' in data:
                    product.name = data['name']
                if 'description' in data:
                    product.description = data['description']
                if 'price' in data:
                    product.price = data['price']  # Validation happens in @validates
                if 'stock' in data:
                    product.stock = data['stock']  # Validation happens in @validates

                # Track who updated
                product.updated_by = current_user

                # Commit changes
                session.commit()

                # Extract data before closing session
                product_data = {
                    'id': product.id,
                    'name': product.name,
                    'description': product.description,
                    'price': product.price,
                    'stock': product.stock,
                    'updated_at': product.updated_at
                }

                logger.info(f"Updated product: {product.name} by {current_user}")
                return product_data

            except ValueError as e:
                session.rollback()
                logger.error(f"Validation error: {str(e)}")
                raise
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error updating product: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("update_product", _operation)

    def update_order_status(self, order_id, new_status, current_user="system"):
        """Update an order's status with proper validation"""

        def _operation():
            session = self.Session()
            try:
                # Retrieve order
                order = session.query(Order).filter(Order.id == order_id).first()
                if not order:
                    raise ValueError(f"Order with ID {order_id} not found")

                # Update status (validation happens in @validates)
                order.status = new_status
                order.updated_by = current_user

                # Commit changes
                session.commit()

                # Extract data before closing session
                order_data = {
                    'id': order.id,
                    'user_id': order.user_id,
                    'status': order.status,
                    'order_date': order.order_date,
                    'updated_at': order.updated_at
                }

                logger.info(f"Updated order status: Order #{order.id} to {new_status} by {current_user}")
                return order_data

            except ValueError as e:
                session.rollback()
                logger.error(f"Validation error: {str(e)}")
                raise
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error updating order: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("update_order_status", _operation)

    def update_order_item(self, item_id, quantity, current_user="system"):
        """Update an order item's quantity with stock management"""

        def _operation():
            session = self.Session()
            try:
                # Retrieve order item with related product (for stock management)
                item = session.query(OrderItem).options(
                    joinedload(OrderItem.product)
                ).filter(OrderItem.id == item_id).first()

                if not item:
                    raise ValueError(f"Order item with ID {item_id} not found")

                # Get the product with lock for update
                product = session.query(Product).filter(
                    Product.id == item.product_id
                ).with_for_update().first()

                # Calculate stock difference
                quantity_diff = quantity - item.quantity

                # Check if enough stock for increase
                if quantity_diff > 0 and product.stock < quantity_diff:
                    raise ValueError(f"Insufficient stock for product {product.name}")

                # Update product stock
                product.stock -= quantity_diff

                # Update item quantity (validation happens in @validates)
                item.quantity = quantity
                item.updated_by = current_user

                # Commit changes
                session.commit()

                # Extract data before closing session
                item_data = {
                    'id': item.id,
                    'order_id': item.order_id,
                    'product_id': item.product_id,
                    'product_name': product.name,
                    'quantity': item.quantity,
                    'price': item.price,
                    'updated_at': item.updated_at
                }

                logger.info(f"Updated order item: Item #{item.id} quantity to {quantity} by {current_user}")
                return item_data

            except ValueError as e:
                session.rollback()
                logger.error(f"Validation error: {str(e)}")
                raise
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error updating order item: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("update_order_item", _operation)

    def update_product_stock(self, product_id, quantity_change, reason, current_user="system"):
        """Update product stock with audit trail"""

        def _operation():
            session = self.Session()
            try:
                # Get product with lock
                product = session.query(Product).filter(
                    Product.id == product_id
                ).with_for_update().first()

                if not product:
                    raise ValueError(f"Product with ID {product_id} not found")

                # Calculate new stock level
                new_stock = product.stock + quantity_change

                # Validate new stock level
                if new_stock < 0:
                    raise ValueError("Stock cannot be negative")

                # Update stock
                product.stock = new_stock
                product.updated_by = current_user

                # Commit changes
                session.commit()

                # Log stock change with reason
                logger.info(f"Stock updated for {product.name}: {quantity_change} units ({reason}) by {current_user}")

                # Extract data before closing session
                product_data = {
                    'id': product.id,
                    'name': product.name,
                    'stock': product.stock,
                    'updated_at': product.updated_at
                }

                return product_data

            except ValueError as e:
                session.rollback()
                logger.error(f"Validation error: {str(e)}")
                raise
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error updating stock: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("update_product_stock", _operation)

    def delete_user(self, user_id, cascade=False, current_user="system"):
        """
        Delete a user from the database

        Args:
            user_id: ID of the user to delete
            cascade: If True, delete all related orders. If False, will error if orders exist
            current_user: Username for audit trail
        """

        def _operation():
            session = self.Session()
            try:
                # Find user with a lock to prevent concurrent modification
                user = session.query(User).filter(User.id == user_id).with_for_update().first()
                if not user:
                    raise ValueError(f"User with ID {user_id} not found")

                # Check if user has orders
                orders_count = session.query(Order).filter(Order.user_id == user_id).count()
                if orders_count > 0 and not cascade:
                    raise ValueError(f"User has {orders_count} orders. Set cascade=True to delete them too")

                # Prepare user info for logging before deletion
                username = user.username

                # Delete the user (with cascade if configured in the model)
                session.delete(user)
                session.commit()

                logger.info(f"User {username} (ID: {user_id}) deleted by {current_user}")
                return True

            except ValueError as e:
                session.rollback()
                logger.error(f"Validation error: {str(e)}")
                raise
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error deleting user: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("delete_user", _operation)

    def delete_product(self, product_id, force=False, current_user="system"):
        """
        Delete a product from the database

        Args:
            product_id: ID of the product to delete
            force: If True, will delete even if product is in orders
            current_user: Username for audit trail
        """

        def _operation():
            session = self.Session()
            try:
                # Find product with a lock
                product = session.query(Product).filter(Product.id == product_id).with_for_update().first()
                if not product:
                    raise ValueError(f"Product with ID {product_id} not found")

                # Check if product is in any order
                used_in_orders = session.query(OrderItem).filter(OrderItem.product_id == product_id).count() > 0
                if used_in_orders and not force:
                    raise ValueError("Cannot delete product that is used in orders. Set force=True to override")

                # Prepare product info for logging before deletion
                product_name = product.name

                # Delete the product
                session.delete(product)
                session.commit()

                logger.info(f"Product {product_name} (ID: {product_id}) deleted by {current_user}")
                return True

            except ValueError as e:
                session.rollback()
                logger.error(f"Validation error: {str(e)}")
                raise
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error deleting product: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("delete_product", _operation)

    def delete_order(self, order_id, current_user="system"):
        """
        Delete an order and return stock to inventory

        Args:
            order_id: ID of the order to delete
            current_user: Username for audit trail
        """

        def _operation():
            session = self.Session()
            try:
                # Find order with eager loading of items
                order = session.query(Order).options(
                    joinedload(Order.order_items)
                ).filter(Order.id == order_id).with_for_update().first()

                if not order:
                    raise ValueError(f"Order with ID {order_id} not found")

                # Return stock for each item
                for item in order.order_items:
                    product = session.query(Product).filter(
                        Product.id == item.product_id
                    ).with_for_update().first()

                    if product:
                        product.stock += item.quantity
                        logger.info(f"Returned {item.quantity} units to product {product.name} stock")

                # Delete the order (cascade deletes items)
                session.delete(order)
                session.commit()

                logger.info(f"Order #{order_id} deleted by {current_user}")
                return True

            except ValueError as e:
                session.rollback()
                logger.error(f"Validation error: {str(e)}")
                raise
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error deleting order: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("delete_order", _operation)

    def delete_order_item(self, item_id, current_user="system"):
        """
        Delete a specific order item and return stock to inventory

        Args:
            item_id: ID of the order item to delete
            current_user: Username for audit trail
        """

        def _operation():
            session = self.Session()
            try:
                # Find order item
                item = session.query(OrderItem).filter(OrderItem.id == item_id).first()
                if not item:
                    raise ValueError(f"Order item with ID {item_id} not found")

                # Get product to update stock
                product = session.query(Product).filter(
                    Product.id == item.product_id
                ).with_for_update().first()

                # Return stock if product exists
                if product:
                    product.stock += item.quantity
                    logger.info(f"Returned {item.quantity} units to product {product.name} stock")

                # Delete the item
                order_id = item.order_id
                session.delete(item)

                # If this was the last item, consider deleting the order too
                remaining_items = session.query(OrderItem).filter(OrderItem.order_id == order_id).count()
                if remaining_items == 0:
                    logger.warning(f"Order #{order_id} now has no items")

                session.commit()

                logger.info(f"Order item #{item_id} deleted by {current_user}")
                return True

            except ValueError as e:
                session.rollback()
                logger.error(f"Validation error: {str(e)}")
                raise
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error deleting order item: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("delete_order_item", _operation)

    def soft_delete_user(self, user_id, current_user="system"):
        """
        Soft delete a user by marking them as inactive rather than removing the record

        Args:
            user_id: ID of the user to soft delete
            current_user: Username for audit trail
        """

        def _operation():
            session = self.Session()
            try:
                # Add a 'is_active' column to User model first
                # This is a hypothetical method assuming you have this column

                user = session.query(User).filter(User.id == user_id).with_for_update().first()
                if not user:
                    raise ValueError(f"User with ID {user_id} not found")

                # Mark as inactive instead of deleting
                user.is_active = False
                user.updated_by = current_user

                # You could also rename the email to prevent reuse
                user.email = f"deleted_{user.email}"
                user.username = f"deleted_{user.username}"

                session.commit()

                logger.info(f"User {user.username} (ID: {user_id}) soft deleted by {current_user}")

                # Return data about the soft-deleted user
                return {
                    'id': user.id,
                    'username': user.username,
                    'is_active': False
                }

            except ValueError as e:
                session.rollback()
                logger.error(f"Validation error: {str(e)}")
                raise
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error soft deleting user: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("soft_delete_user", _operation)

    def bulk_delete_products(self, product_ids, current_user="system"):
        """
        Delete multiple products in a single transaction

        Args:
            product_ids: List of product IDs to delete
            current_user: Username for audit trail
        """

        def _operation():
            session = self.Session()
            try:
                deleted_count = 0
                errors = []

                # Check if any products are used in orders
                used_products = session.query(OrderItem.product_id).filter(
                    OrderItem.product_id.in_(product_ids)
                ).distinct().all()

                used_product_ids = [p[0] for p in used_products]
                if used_product_ids:
                    raise ValueError(f"Products with IDs {used_product_ids} are used in orders and cannot be deleted")

                # Delete products that are not in orders
                for product_id in product_ids:
                    product = session.query(Product).filter(Product.id == product_id).with_for_update().first()
                    if product:
                        product_name = product.name
                        session.delete(product)
                        logger.info(f"Product {product_name} (ID: {product_id}) deleted by {current_user}")
                        deleted_count += 1
                    else:
                        errors.append(f"Product with ID {product_id} not found")

                # Commit all deletions in one transaction
                session.commit()

                result = {
                    'success': True,
                    'deleted_count': deleted_count,
                    'errors': errors
                }

                return result

            except ValueError as e:
                session.rollback()
                logger.error(f"Validation error: {str(e)}")
                raise
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Database error bulk deleting products: {str(e)}")
                raise
            finally:
                session.close()

        return execute_with_retry("bulk_delete_products", _operation)

    def delete_database(self):
        """Delete the SQLite database file"""
        # Ensure all connections are closed
        self.engine.dispose()

        # Get database file path from engine URL
        db_path = self.engine.url.database

        try:
            if os.path.exists(db_path):
                os.remove(db_path)
                logger.info(f"Database file {db_path} successfully deleted")
                return True
            else:
                logger.warning(f"Database file {db_path} does not exist")
                return False
        except Exception as e:
            logger.error(f"Error deleting database: {str(e)}")
            raise


# Create the engine
engine = create_engine('sqlite:///ecommerce.db', echo=False)

# Create all tables
Base.metadata.create_all(engine)

# Initialize the database manager
db_manager = DatabaseManager(engine)

# Example usage with proper exception handling
try:
    # Create a user
    user = db_manager.create_user(
        username="johndoe",
        email="john.doe@example.com",
        password="secure_password",
        current_user="admin"
    )

    # Create products
    product1 = db_manager.create_product(
        name="Laptop",
        description="High-performance laptop",
        price=999.99,
        stock=10,
        current_user="admin"
    )

    product2 = db_manager.create_product(
        name="Mouse",
        description="Wireless mouse",
        price=29.99,
        stock=50,
        current_user="admin"
    )

    # Create an order with items
    order = db_manager.create_order(
        user_id=user['id'],
        items=[
            {"product_id": product1['id'], "quantity": 1},
            {"product_id": product2['id'], "quantity": 2}
        ],
        current_user="admin"
    )

    print(f"Created order #{order['id']} for user {user['username']}")

except Exception as e:
    print(f"Error: {str(e)}")

try:
    # Get a specific user
    user_data = db_manager.get_user(1)
    print(f"Retrieved user: {user_data['username']}")

    # Get a product
    product_data = db_manager.get_product(1)
    print(f"Retrieved product: {product_data['name']} - ${product_data['price']}")

    # Get complete order with items
    order_data = db_manager.get_order_with_items(1)
    if order_data:
        print(f"Order #{order_data['id']} has {len(order_data['items'])} items")
        for item in order_data['items']:
            print(f"  - {item['product_name']}: {item['quantity']} x ${item['price']}")

    # List products with filtering
    products = db_manager.list_products(page=1, page_size=5, min_price=20, search="lap")
    print(f"Found {products['total']} products, showing {len(products['products'])}")

    # Get user orders
    user_orders = db_manager.get_user_orders(user_data['id'])
    print(f"User has {user_orders['total']} orders")

except Exception as e:
    print(f"Error: {str(e)}")

try:
    # Update user information
    updated_user = db_manager.update_user(
        user_id=1,
        data={
            'username': 'john_doe_updated',
            'email': 'john.updated@example.com'
        },
        current_user='admin'
    )
    print(f"Updated user: {updated_user['username']}")

    # Update product details and price
    updated_product = db_manager.update_product(
        product_id=1,
        data={
            'description': 'Updated high-performance gaming laptop',
            'price': 1099.99
        },
        current_user='admin'
    )
    print(f"Updated product: {updated_product['name']} - ${updated_product['price']}")

    # Update order status
    updated_order = db_manager.update_order_status(
        order_id=1,
        new_status='completed',
        current_user='admin'
    )
    print(f"Updated order status to: {updated_order['status']}")

    # Update order item quantity
    updated_item = db_manager.update_order_item(
        item_id=1,
        quantity=2,
        current_user='admin'
    )
    print(f"Updated item quantity to: {updated_item['quantity']}")

    # Update product stock (e.g., received new inventory)
    restocked_product = db_manager.update_product_stock(
        product_id=1,
        quantity_change=5,
        reason="Restock from supplier",
        current_user='admin'
    )
    print(f"Restocked {restocked_product['name']} to {restocked_product['stock']} units")

except Exception as e:
    print(f"Error: {str(e)}")

try:
    # Delete an order and return stock to inventory
    db_manager.delete_order(order_id=1, current_user="admin")
    print("Order successfully deleted")

    # Delete a product (only if not used in orders)
    db_manager.delete_product(product_id=2, current_user="admin")
    print("Product successfully deleted")

    # Delete a user with all their orders
    db_manager.delete_user(user_id=1, cascade=True, current_user="admin")
    print("User and all their orders successfully deleted")

    # Bulk delete multiple products
    result = db_manager.bulk_delete_products(
        product_ids=[1, 3, 4, 5],
        current_user="admin"
    )
    print(f"Deleted {result['deleted_count']} products")

except Exception as e:
    print(f"Error: {str(e)}")

try:
    # Adding users
    user_data = [
        ("Alice", "alice@example.com", "secure_password", "admin"),
        ("Bob", "bob@example.com", "secure_password", "admin"),
        ("Charlie", "charlie@example.com", "secure_password", "admin"),
        ("David", "david@example.com", "secure_password", "admin"),
        ("Eve", "eve@example.com", "secure_password", "admin"),
        ("Frank", "frank@example.com", "secure_password", "admin"),
        ("Grace", "grace@example.com", "secure_password", "admin"),
        ("Heidi", "heidi@example.com", "secure_password", "admin"),
        ("Ivan", "ivan@example.com", "secure_password", "admin"),
        ("Judy", "judy@example.com", "secure_password", "admin")
    ]
    for name, email, password, created_by in user_data:
        db_manager.create_user(name, email, password, created_by)

    print("Bulk users added successfully")

    # Adding products
    product_data = [
        ("Smartphone", "Latest model smartphone", 699.99, 200),
        ("Tablet", "High-resolution tablet", 499.99, 1500),
        ("Headphones", "Noise-cancelling headphones", 199.99, 300),
        ("Smartwatch", "Fitness tracking smartwatch", 249.99, 250),
        ("Charger", "Fast charging wall adapter", 29.99, 1000),
        ("USB Cable", "High-speed USB cable", 9.99, 2000),
        ("Bluetooth Speaker", "Portable Bluetooth speaker", 149.99, 500),
        ("Wireless Charger", "Qi wireless charger", 39.99, 750),
        ("Laptop Stand", "Ergonomic laptop stand", 59.99, 400),
        ("Webcam", "1080p HD webcam", 89.99, 600),
        ("External Hard Drive", "1TB external hard drive", 79.99, 350),
        ("Portable SSD", "500GB portable SSD", 129.99, 200),
        ("Gaming Mouse", "High-precision gaming mouse", 59.99, 450),
        ("Mechanical Keyboard", "RGB mechanical keyboard", 89.99, 300),
        ("Monitor Stand", "Adjustable monitor stand", 49.99, 500),
        ("Desk Organizer", "Multi-compartment desk organizer", 19.99, 800),
        ("Laptop Sleeve", "Padded laptop sleeve", 29.99, 1000),
        ("Screen Protector", "Tempered glass screen protector", 14.99, 1500),
        ("HDMI Cable", "High-speed HDMI cable", 12.99, 2000),
        ("Ethernet Cable", "Cat6 Ethernet cable", 9.99, 2500)
    ]
    for name, description, price, stock in product_data:
        db_manager.create_product(name, price, description, stock)

    print("Bulk products added successfully")

    # Adding orders for each user with at lest 3 items for each order
    products = db_manager.list_products(page=1, page_size=100)['products']
    for user in db_manager.list_users(page=1, page_size=100)['users']:
        items = []
        for i in range(3):
            product_index = i % len(products)
            items.append({
                "product_id": products[product_index]['id'],
                "quantity": i + 1
            })
        db_manager.create_order(user['id'], items, "admin")

    print("Bulk orders added successfully")

except Exception as e:
    print(f"Error: {str(e)}")

# Example of the functions
try:
    # Get all the total quantity sold for each product
    total_quantity_sold = db_manager.get_total_quantity_sold()
    print("Total quantity sold for each product:")

    for item in total_quantity_sold:
        print(f"Product: {item['product_name']}, Total Sold: {item['total_quantity_sold']}")

except Exception as e:
    print(f"Error: {str(e)}")

# Example of soft deleting a user
try:
    # Create a new user first
    new_user = db_manager.create_user(
        username="temporary_user",
        email="temp@example.com",
        password="temp_password",
        current_user="admin"
    )

    # Soft delete the user
    soft_deleted = db_manager.soft_delete_user(
        user_id=new_user['id'],
        current_user="admin"
    )
    print(f"User {soft_deleted['username']} soft deleted successfully")

except Exception as e:
    print(f"Error with soft delete: {str(e)}")

# Delete database
try:
    # Ensure all sessions are closed
    result = db_manager.delete_database()
    if result:
        print("Database successfully deleted")
    else:
        print("Database file not found")

except Exception as e:
    print(f"Error deleting database: {str(e)}")
