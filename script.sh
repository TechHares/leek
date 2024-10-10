# 检查是否传入了足够的参数
if [ "$#" -ne 1 ]; then
    echo "请传入动作 start|stop|restart "
    exit 1
fi
version=$(grep 'VERSION' leek/common/config.py)
echo "echo 当前程序$version"
action=$1
# 定义启动服务的函数
start_service() {
    echo "Starting the service..."
    nohup python3.13 main.py >> console.log 2>&1 &
}

# 定义停止服务的函数
stop_service() {
    echo "Stopping the service..."
    ps -efx|grep python|grep main.py|grep leek|awk '{print $1}'|xargs kill
}

case $action in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        echo "Restarting the service..."
        stop_service
        echo "Waiting for 5 seconds..."
        sleep 5
        start_service
        ;;
    *)
        echo "无效的动作: $action"
        echo "请使用: $0 {start|stop|restart}"
        exit 1
        ;;
esac
