# *******************************************************************************
# Name: index.py
# Description: A python script to automatically tag AWS resources.
#
# Oct. 28 2019, JingKun Technology Co. Ltd
# *******************************************************************************

from __future__ import print_function
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)
businessUnit = ''


def lambda_handler(event, context):
    detail = event['detail']
    eventname = detail['eventName']
    region = str(event['region'])
    detail = event['detail']
    userType = detail['userIdentity']['type']
    iam = boto3.resource('iam')

    global businessUnit
    # 判断事件是来自 User 实体还是来自 Role
    if userType == 'IAMUser':
        user = detail['userIdentity']['userName']
    else:
        # 若非实体用户则从 principal 中截取 Role 的信息
        principal = detail['userIdentity']['principalId']
        user = principal.split(':')[1]
    if iam.User(user).tags:
        for item in iam.User(user).tags:
            if item['Key'] == 'BusinessUnit':
                businessUnit = item['Value']
    if not businessUnit:
        businessUnit = 'undefined'
        
    # logger.info('principalId: ' + str(principal))
    logger.info('eventName: ' + str(eventname))
    logger.info('event: ' + str(event))
    logger.setLevel(logging.INFO)

    if eventname == 'RunInstances':
        # 启动EC2实例
        ids = []
        ec2 = boto3.resource('ec2')
        items = detail['responseElements']['instancesSet']['items']
        for item in items:
            ids.append(item['instanceId'])
        logger.info(ids)
        logger.info('number of instances: ' + str(len(ids)))

        base = ec2.instances.filter(InstanceIds=ids)
        # 遍历实例寻找附加的卷和网络接口
        for instance in base:
            for vol in instance.volumes.all():
                ids.append(vol.id)
            for eni in instance.network_interfaces:
                ids.append(eni.id)
        if ids:
            for resourceId in ids:
                print('Tagging resource ' + resourceId)
            ec2.create_tags(Resources=ids,
                            Tags=[{'Key': 'CreateBy', 'Value': user},
                                  {'Key': 'BusinessUnit', 'Value': businessUnit}])
            print('Auto Tagging completed with "CreateBy:' + user + 
                                    '" and "BusinessUnit:' + businessUnit + '"')

    elif eventname in ('CreateVolume', 'RegisterImage', 'CreateSnapshot', 'CreateVpc', 'AllocateAddress'):
        # 创建EC2卷、镜像、快照、VPC或弹性IP
        id = []
        ec2 = boto3.resource('ec2')
        if eventname == 'CreateVolume':
            id.append(detail['responseElements']['volumeId'])
            
        elif eventname == 'RegisterImage':
            id.append(detail['responseElements']['imageId'])

        elif eventname == 'CreateSnapshot':
            id.append(detail['responseElements']['snapshotId'])
            
        elif eventname == 'CreateVpc':
            id.append(detail['responseElements']['vpc']['vpcId'])
            
        elif eventname == 'AllocateAddress':
            id.append(detail['responseElements']['allocationId'])
        if id:
            print('Tagging resource ' + str(id))
        ec2.create_tags(Resources=id,Tags=[{'Key': 'CreateBy', 'Value': user}, 
                                           {'Key': 'BusinessUnit', 'Value': businessUnit}])
        print('Auto Tagging completed with "CreateBy:' + user + 
                                '" and "BusinessUnit:' + businessUnit + '"')

    elif eventname == 'CreateLoadBalancer':
        #创建负载均衡器
        lb_name=[]
        lb_name.append(detail['requestParameters']['loadBalancerName'])
        client = boto3.client('elb')
        print('Tagging resource ' + str(lb_name))
        tags = [{'Key': 'CreateBy', 'Value': user},
                {'Key': 'BusinessUnit', 'Value': businessUnit}]
        client.add_tags(LoadBalancerNames = lb_name, Tags = tags)
        print('Auto Tagging completed with "CreateBy:' + user + 
                                '" and "BusinessUnit:' + businessUnit + '"')
        
    elif eventname == 'CreateTable':
        # 创建Dynamodb表
        client = boto3.client('dynamodb')
        resource_arn = detail['responseElements']['tableDescription']['tableArn']
        table_name = detail['responseElements']['tableDescription']['tableName']
        print('Tagging resource ' + table_name)
        tags = [{'Key': 'CreateBy', 'Value': user},
                {'Key': 'BusinessUnit', 'Value': businessUnit}]
        client.tag_resource(ResourceArn = resource_arn, Tags = tags)
        print('Auto Tagging completed with "CreateBy:' + user + 
                                '" and "BusinessUnit:' + businessUnit + '"')

    elif eventname == 'CreateFunction20150331':
        # 创建Lambda功能
        # Lambda 的实际 API 与文档中并不一致, 其组成为 Api 名字+版本
        client = boto3.client('lambda')
        function_name = detail['requestParameters']['functionName']
        # Lambda 函数的 arn
        function_arn = detail['responseElements']['functionArn']
        print('Tagging resource ' + function_name)
        tags = {'CreateBy': user, 'BusinessUnit': businessUnit}
        client.tag_resource(Resource=function_arn, Tags=tags)
        print('Auto Tagging completed with "CreateBy:' + user + 
                                '" and "BusinessUnit:' + businessUnit + '"')

    elif eventname == 'CreateDBInstance':
        # 创建RDS实例
        client = boto3.client('rds')
        resource_arn = detail['responseElements']['dBInstanceArn']
        db_name = detail['responseElements']['dBName']
        print('Tagging resource ' + db_name)
        tags = [{'Key': 'CreateBy', 'Value': user},
                {'Key': 'BusinessUnit', 'Value': businessUnit}]
        client.add_tags_to_resource(ResourceName=resource_arn, Tags=tags)
        print('Auto Tagging completed with "CreateBy:' + user + 
                                '" and "BusinessUnit:' + businessUnit + '"')

    elif eventname == 'CreateCluster':
        # 创建RedShift集群
        client = boto3.client('redshift')
        cluster_name = detail['requestParameters']['clusterIdentifier']
        account_id = event['account']
        # 在 API 中并没有提供获取 RedShift ARN 的方法，需要自己手动拼接，中国区的 ARN 形如：
        # arn:aws-cn:redshift:region:account-id:cluster:cluster-name
        # 拼接 arn
        resource_arn = "arn:aws-cn:redshift:" + str(region) + ":" + str(account_id) + ":cluster:" + cluster_name
        print('Tagging resource ' + cluster_name)
        tags = [{'Key': 'CreateBy', 'Value': user},
                {'Key': 'BusinessUnit', 'Value': businessUnit}]
        client.create_tags(ResourceName=resource_arn, Tags=tags)
        print('Auto Tagging completed with "CreateBy:' + user + 
                                '" and "BusinessUnit:' + businessUnit + '"')

    elif eventname == 'CreateBucket':
        # 创建S3桶
        s3 = boto3.client("s3")
        bucket_name = detail['requestParameters']['bucketName']
        print('Tagging resource ' + bucket_name)
        tags = [{'Key': 'CreateBy', 'Value': user},
                {'Key': 'BusinessUnit', 'Value': businessUnit}]
        s3.put_bucket_tagging(Bucket=bucket_name, Tagging={'TagSet': tags})
        print('Auto Tagging completed with "CreateBy:' + user + 
                                '" and "BusinessUnit:' + businessUnit + '"')

    elif eventname == 'PutObject':
        # 向S3上传文件
        s3 = boto3.client("s3")
        bucket_name = detail['requestParameters']['bucketName']
        object_name = detail['requestParameters']['key']
        print('Tagging object ' + bucket_name + '/' + object_name)
        tags = [{'Key': 'CreateBy', 'Value': user},
                {'Key': 'BusinessUnit', 'Value': businessUnit}]
        s3.put_object_tagging(Bucket=bucket_name, Key=object_name, Tagging={'TagSet': tags})
        print('Auto Tagging completed with "CreateBy:' + user + 
                                '" and "BusinessUnit:' + businessUnit + '"')

    elif eventname == 'CreateQueue':
        # 创建SQS队列
        client = boto3.client('sqs')
        queue_url = detail['responseElements']['queueUrl']
        queue_name = detail['requestParameters']['queueName']
        print('Tagging resource ' + queue_name)
        tags = {'CreateBy': user, 'BusinessUnit': businessUnit}
        client.tag_queue(QueueUrl=queue_url, Tags=tags)
        print('Auto Tagging completed with "CreateBy:' + user + 
                                '" and "BusinessUnit:' + businessUnit + '"')
        

    # elif eventname == 'CreateVpc':
    #     # 创建VPC
    #     vpc_id = detail['responseElements']['vpc']['vpcId']
    #     ec2 = boto3.resource('ec2')
    #     vpc = ec2.Vpc(vpc_id)
    #     print('Tagging resource ' + vpc_id)
    #     tags = [{'Key': 'CreateBy', 'Value': user},
    #             {'Key': 'BusinessUnit', 'Value': businessUnit}]
    #     vpc.create_tags(DryRun=False, Tags=tags)
    #     print('Auto Tagging completed with "CreateBy:' + user + 
    #                             '" and "BusinessUnit:' + businessUnit + '"')
        
    else:
        logger.warning('Not supported action')
        return False

    logger.info("Success!")
    return True
