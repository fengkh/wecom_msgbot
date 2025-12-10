import pika
import ssl
import json
import logging
import time
from typing import Dict, Any, Optional, Callable
import signal
import sys
from datetime import datetime
import threading
from typing import Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("RabbitMQ-SSL")


class SSLRabbitMQConsumer:
    """支持SSL的RabbitMQ消费者"""

    def __init__(self, config: Dict[str, Any] = None):
        # 默认配置
        self.default_config = {
            'host': '192.168.2.106',
            'port': 5671,
            'virtual_host': '/',
            'username': 'rabbitmq',
            'password': 'rabbitmq',
            'routing_key': '',  # 路由键
            'durable': True,
            'listener': {
                'concurrency': 1,  # 初始并发数
                'max_concurrency': 10,  # 最大并发数
                'prefetch_count': 1  # QoS预取数量
            },

            'connection': {
                'heartbeat': 600,  # 心跳间隔(秒)
                'blocked_connection_timeout': 300,  # 阻塞超时
                'connection_attempts': 5,  # 连接尝试次数
                'retry_delay': 5,  # 重试延迟
                'socket_timeout': 10  # socket超时
            }
        }

        # 合并配置
        if config:
            self._merge_config(config)

        # 连接状态
        self.connection = None
        self.channel = None
        self.is_connected = False
        self.should_reconnect = True
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10

        # 消费者相关
        self.consumer_tag = None
        self.message_handler = None
        self.active_consumers = 0
        self.max_consumers = self.default_config['listener']['max_concurrency']

        # 统计
        self.metrics = {
            'messages_received': 0,
            'messages_processed': 0,
            'messages_failed': 0,
            'connection_errors': 0,
            'last_connection_time': None,
            'uptime_start': datetime.now()
        }

    def _merge_config(self, config: Dict[str, Any]):
        """深度合并配置"""

        def deep_update(base, update):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    deep_update(base[key], value)
                else:
                    base[key] = value

        deep_update(self.default_config, config)

    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """创建SSL上下文"""
        try:
            ssl_context = ssl.create_default_context(
                cafile=self.default_config['ssl']['ca_certs']
            )

            # 设置协议版本
            ssl_context.protocol = self.default_config['ssl']['ssl_version']

            # 设置证书验证
            ssl_context.verify_mode = self.default_config['ssl']['cert_reqs']

            # 加载客户端证书（如果提供）
            if (self.default_config['ssl']['certfile'] and
                    self.default_config['ssl']['keyfile']):
                ssl_context.load_cert_chain(
                    certfile=self.default_config['ssl']['certfile'],
                    keyfile=self.default_config['ssl']['keyfile']
                )

            # 禁用不安全的协议
            ssl_context.options |= ssl.OP_NO_SSLv2
            ssl_context.options |= ssl.OP_NO_SSLv3
            ssl_context.options |= ssl.OP_NO_TLSv1
            ssl_context.options |= ssl.OP_NO_TLSv1_1

            return ssl_context
        except Exception as e:
            logger.error(f"创建SSL上下文失败: {e}")
            return None

    def connect(self) -> bool:
        """建立SSL连接"""
        try:
            logger.info("正在建立SSL连接...")
            logger.info(f"主机: {self.default_config['host']}:{self.default_config['port']}")
            logger.info(f"虚拟主机: {self.default_config['virtual_host']}")
            logger.info(f"用户名: {self.default_config['username']}")

            # 创建SSL上下文
            ssl_context = self._create_ssl_context()
            ssl_options = None
            if ssl_context:
                ssl_options = pika.SSLOptions(ssl_context, self.default_config['host'])

            # 连接参数
            credentials = pika.PlainCredentials(
                username=self.default_config['username'],
                password=self.default_config['password']
            )

            parameters = pika.ConnectionParameters(
                host=self.default_config['host'],
                port=self.default_config['port'],
                virtual_host=self.default_config['virtual_host'],
                credentials=credentials,
                heartbeat=self.default_config['connection']['heartbeat'],
                blocked_connection_timeout=self.default_config['connection']['blocked_connection_timeout'],
                connection_attempts=self.default_config['connection']['connection_attempts'],
                retry_delay=self.default_config['connection']['retry_delay'],
                socket_timeout=self.default_config['connection']['socket_timeout'],
                ssl_options=ssl_options
            )

            # 建立连接
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()

            # 设置QoS
            self.channel.basic_qos(
                prefetch_count=self.default_config['listener']['prefetch_count']
            )

            self.is_connected = True
            self.reconnect_attempts = 0
            self.metrics['last_connection_time'] = datetime.now()
            self.metrics['connection_errors'] = 0

            logger.info("✅ SSL连接成功建立")
            logger.info(f"心跳: {self.default_config['connection']['heartbeat']}秒")
            logger.info(f"预取数: {self.default_config['listener']['prefetch_count']}")

            return True

        except ssl.SSLError as e:
            logger.error(f"❌ SSL握手失败: {e}")
            logger.info("请检查:")
            logger.info("1. 是否正确配置了证书")
            logger.info("2. 服务器证书是否有效")
            logger.info("3. 是否使用了正确的协议版本")
        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"❌ AMQP连接失败: {e}")
        except Exception as e:
            logger.error(f"❌ 连接时发生未知错误: {e}")
            logger.exception("详细错误信息:")

        self.is_connected = False
        self.metrics['connection_errors'] += 1
        return False

    def declare_queue(self, queue_name: str, **kwargs) -> bool:
        """声明队列"""
        try:
            if not self.is_connected:
                logger.error("未连接，无法声明队列")
                return False

            # 合并参数
            queue_args = {
                'queue': queue_name,
                'durable': self.default_config.get('durable', True),
                # 'exclusive': False,
                # 'auto_delete': False,
                # 'arguments': {
                #     # 'x-message-ttl': 604800000,  # 7天过期
                #     'x-max-length': 10000,  # 最大消息数
                #     'x-dead-letter-exchange': f'dlx.{queue_name}',  # 死信交换机
                #     'x-dead-letter-routing-key': f'dlx.{queue_name}'  # 死信路由键
                # }
            }
            queue_args.update(kwargs)

            result = self.channel.queue_declare(**queue_args)

            # 声明对应的死信队列
            dlx_args = queue_args.copy()
            dlx_args['queue'] = f'dlx.{queue_name}'
            dlx_args['arguments'] = {}  # 死信队列不设置死信
            self.channel.queue_declare(**dlx_args)

            logger.info(f"✅ 队列声明成功: {queue_name}")
            logger.info(f"   消息数: {result.method.message_count}")
            logger.info(f"   消费者数: {result.method.consumer_count}")
            logger.info(f"   死信队列: dlx.{queue_name}")

            return True

        except Exception as e:
            logger.error(f"队列声明失败: {e}")
            return False

    def setup_exchange(self, exchange_name: str, exchange_type: str = 'direct') -> bool:
        """设置交换机"""
        try:
            if not self.is_connected:
                return False

            self.channel.exchange_declare(
                exchange=exchange_name,
                exchange_type=exchange_type,
                durable=True
            )

            logger.info(f"交换机声明成功: {exchange_name} ({exchange_type})")
            return True
        except Exception as e:
            logger.error(f"交换机声明失败: {e}")
            return False

    def bind_queue(self, queue_name: str, exchange_name: str, routing_key: str) -> bool:
        """绑定队列到交换机"""
        try:
            self.channel.queue_bind(
                exchange=exchange_name,
                queue=queue_name,
                routing_key=routing_key
            )
            logger.info(f"队列绑定成功: {queue_name} -> {exchange_name}[{routing_key}]")
            return True
        except Exception as e:
            logger.error(f"队列绑定失败: {e}")
            return False

    def on_message_callback(self, ch, method, properties, body):
        """消息处理回调"""
        message_id = properties.message_id or f"msg_{self.metrics['messages_received']}"
        self.metrics['messages_received'] += 1

        logger.info(f"📨 收到消息 [ID: {message_id}]")

        try:
            # 解析消息
            message_data = json.loads(body.decode('utf-8'))
            logger.debug(f"消息内容: {json.dumps(message_data, ensure_ascii=False, indent=2)}")

            # 处理消息
            if self.message_handler:
                try:
                    result = self.message_handler(message_data, properties)
                    if result is True:
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        self.metrics['messages_processed'] += 1
                        logger.info(f"✅ 消息处理成功: {message_id}")
                    elif result is False:
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                        self.metrics['messages_failed'] += 1
                        logger.warning(f"❌ 消息处理失败(丢弃): {message_id}")
                    else:  # None或其他
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                        logger.warning(f"⚠️ 消息处理失败(重试): {message_id}")
                except Exception as e:
                    logger.error(f"自定义处理器异常: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            else:
                # 无处理器，直接确认
                ch.basic_ack(delivery_tag=method.delivery_tag)
                self.metrics['messages_processed'] += 1
                logger.info(f"✅ 消息自动确认: {message_id}")

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析失败: {e}")
            logger.debug(f"原始消息: {body[:500]}...")  # 只记录前500字符
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            self.metrics['messages_failed'] += 1
        except Exception as e:
            logger.error(f"❌ 消息处理异常: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            self.metrics['messages_failed'] += 1

    def set_message_handler(self, handler: Callable):
        """设置消息处理器"""
        self.message_handler = handler
        logger.info("自定义消息处理器已设置")

    def start_consuming(self, queue_name: str, auto_ack: bool = False):
        """开始消费消息"""
        if not self.is_connected:
            logger.error("未连接，无法开始消费")
            return

        try:
            # 声明队列
            if not self.declare_queue(queue_name):
                logger.error(f"队列 {queue_name} 声明失败")
                return

            # 启动消费者
            self.consumer_tag = self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=self.on_message_callback,
                auto_ack=auto_ack
            )

            self.active_consumers += 1
            logger.info(f"🚀 开始消费队列: {queue_name}")
            logger.info(f"   并发消费者数: {self.active_consumers}/{self.max_consumers}")

            # 开始消费
            self.channel.start_consuming()

        except pika.exceptions.ConnectionClosedByBroker:
            logger.warning("连接被代理关闭")
            self.is_connected = False
        except pika.exceptions.AMQPChannelError as e:
            logger.error(f"通道错误: {e}")
        except KeyboardInterrupt:
            logger.info("收到键盘中断信号")
        except Exception as e:
            logger.error(f"消费过程异常: {e}")
        finally:
            self.stop_consuming()

    def stop_consuming(self):
        """停止消费"""
        if self.channel and self.consumer_tag:
            try:
                self.channel.basic_cancel(self.consumer_tag)
                self.consumer_tag = None
                self.active_consumers = max(0, self.active_consumers - 1)
                logger.info("消费已停止")
            except Exception as e:
                logger.error(f"停止消费失败: {e}")

    def close(self):
        """关闭连接"""
        self.stop_consuming()

        if self.channel and self.channel.is_open:
            try:
                self.channel.close()
            except Exception:
                pass

        if self.connection and self.connection.is_open:
            try:
                self.connection.close()
            except Exception:
                pass

        self.is_connected = False
        logger.info("连接已关闭")

    def get_metrics(self) -> Dict[str, Any]:
        """获取监控指标"""
        uptime = datetime.now() - self.metrics['uptime_start']
        self.metrics['uptime'] = str(uptime)
        self.metrics['current_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return self.metrics.copy()

    def print_status(self):
        """打印状态信息"""
        metrics = self.get_metrics()
        print("\n" + "=" * 60)
        print("RabbitMQ SSL 连接状态")
        print("=" * 60)
        print(f"连接状态: {'✅ 已连接' if self.is_connected else '❌ 未连接'}")
        print(f"主机: {self.default_config['host']}:{self.default_config['port']}")
        print(f"虚拟主机: {self.default_config['virtual_host']}")
        print(f"消费者数: {self.active_consumers}/{self.max_consumers}")
        print(f"运行时间: {metrics['uptime']}")
        print(f"消息统计:")
        print(f"  接收: {metrics['messages_received']}")
        print(f"  成功: {metrics['messages_processed']}")
        print(f"  失败: {metrics['messages_failed']}")
        print(f"连接错误: {metrics['connection_errors']}")
        print(f"最后连接: {metrics['last_connection_time']}")
        print("=" * 60)


class RabbitMQManager:
    """RabbitMQ连接管理器，支持自动重连"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.consumer = None
        self.running = False
        self.reconnect_thread = None

    def start(self, queue_name: str, message_handler: Callable = None):
        """启动消费者"""
        self.running = True

        def _consumer_loop():
            while self.running:
                try:
                    # 创建消费者实例
                    self.consumer = SSLRabbitMQConsumer(self.config)

                    # 设置消息处理器
                    if message_handler:
                        self.consumer.set_message_handler(message_handler)

                    # 连接
                    if self.consumer.connect():
                        # 开始消费
                        self.consumer.start_consuming(queue_name)
                    else:
                        logger.error("连接失败，等待重试...")
                        time.sleep(10)

                except KeyboardInterrupt:
                    logger.info("收到中断信号")
                    self.running = False
                    break
                except Exception as e:
                    logger.error(f"消费者异常: {e}")
                    if self.consumer:
                        self.consumer.close()
                    time.sleep(5)  # 等待后重试

        # 启动消费者线程
        self.reconnect_thread = threading.Thread(
            target=_consumer_loop,
            name="RabbitMQ-Consumer",
            daemon=True
        )
        self.reconnect_thread.start()
        logger.info("RabbitMQ管理器已启动")

    def stop(self):
        """停止消费者"""
        self.running = False
        if self.consumer:
            self.consumer.close()
        if self.reconnect_thread:
            self.reconnect_thread.join(timeout=5)
        logger.info("RabbitMQ管理器已停止")

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        if self.consumer:
            return self.consumer.get_metrics()
        return {"status": "not_connected"}


def process_message(data: Dict[str, Any], properties) -> bool:
    """
    自定义消息处理器
    返回: True-成功, False-失败(丢弃), None-失败(重试)
    """
    try:
        logger.info(f"开始准备处理消息: {data}")

        # 业务逻辑示例
        if data.get('type') == 'wecom_msgbot':
            logger.info(f"收到竞拍通知，开始处理")
            # mycode here
            return True

        else:
            logger.warning(f"未知消息类型: {data},不予处理")
            return True  # 确认未知类型消息，避免阻塞队列

    except Exception as e:
        logger.error(f"消息处理异常: {e}")
        return None  # 返回None会触发重试


def main():
    """主程序"""
    # 配置
    config = {
        'host': '192.168.2.106',
        'port': 5671,
        'username': 'rabbitmq',
        'password': 'rabbitmq',
        'virtual_host': '/',
        'listener': {
            'concurrency': 1,
            'max_concurrency': 10,
            'prefetch_count': 1
        },

    }

    def signal_handler(signum, frame):
        logger.info(f"收到信号 {signum}，正在关闭...")
        manager.stop()
        sys.exit(0)

    # 注册信号
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 创建管理器
    manager = RabbitMQManager(config)
    # manager = RabbitMQManager()

    # 定义队列名称
    queue_name = 'yilvtong.auction.notice.agency'

    # 启动
    logger.info("启动RabbitMQ SSL消费者...")
    manager.start(queue_name, process_message)

    # 定期打印状态
    def print_status_periodically():
        while manager.running:
            time.sleep(30)  # 每30秒打印一次状态
            if manager.consumer:
                manager.consumer.print_status()

    status_thread = threading.Thread(
        target=print_status_periodically,
        daemon=True
    )
    status_thread.start()

    # 保持主线程运行
    try:
        while manager.running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("主线程被中断")
    finally:
        manager.stop()


if __name__ == '__main__':
    # # 测试连接
    # logger.info("测试RabbitMQ SSL连接...")
    #
    # # 创建测试连接
    # test_consumer = SSLRabbitMQConsumer()
    #
    # if test_consumer.connect():
    #     logger.info("✅ SSL连接测试成功！")
    #
    #     # 测试队列声明
    #     if test_consumer.declare_queue('test.queue'):
    #         logger.info("✅ 队列声明测试成功！")
    #
    #     # 打印状态
    #     test_consumer.print_status()
    #
    #     # 关闭连接
    #     test_consumer.close()
    # else:
    #     logger.error("❌ SSL连接测试失败！")
    #     logger.info("请检查：")
    #     logger.info("1. RabbitMQ服务是否运行在 192.168.2.106:5671")
    #     logger.info("2. 防火墙是否开放5671端口")
    #     logger.info("3. SSL证书配置是否正确")
    #     logger.info("4. 用户名/密码是否正确")
    main()
