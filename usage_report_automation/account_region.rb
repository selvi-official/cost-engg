require 'aws-sdk'
require 'aws-sdk-account'


data_list ={'freshworks-fusion-prod' => '822009091411','freshchat-onboarding-prod'=> '054541145046', 'freshworks-revenue-enablement'=> '593734767363', 'lego-prod'=> '680771906342', 'freshworks-noc'=> '534213410019', 'platform-surveyserv-prod'=> '685654890346', 'platform-search-aurora-prod'=> '471112504528', 'fcp-prod'=> '528075892726', 'freshworks-vault-prod'=> '671891599523', 'freshworks-Jira'=> '554844205586', 'freshworks-revops-prod'=> '232218739256', 'freshworks-teleport-prod'=> '347380034320', 'freddy-freshservice-datascience-prod'=> '713530222627', 'platform-hypertrail-prod'=> '063375560810', 'platform-formserv-prod'=> '170324957714', 'freshworks-payer'=> '031429593201', 'freshworks-logs-prod'=> '034170773883', 'freshworks-corp-apps'=> '037974244722', 'Platforms-prod'=> '659569884990', 'platform-api-gateway-prod'=> '718654219737', 'freshrelease-prod'=> '358630621657', 'freshservice-integration-prod'=> '618708667954', 'platform-infigenic-prod'=> '040574528343', 'fresh-orchestrator-prod'=> '521002495713', 'dp-reports-prod'=> '264112762694', 'freddy-freshsales-prod'=> '594542760018', 'freshworks-it'=> '268013350282', 'fcc-prod'=> '021382806355', 'freshsurvey-prod'=> '140095221187', 'freshworks-ci-tools-prod'=> '792634465463', 'freshping-prod'=> '154461066078', 'freshsuccess-prod'=> '130820453270', 'platforms-channels-prod'=> '059299475013', 'markops-analytics-prod'=> '773636078007', 'ubx-prod'=> '806571990217', 'freshworks-ai-prod'=> '382254873799', 'platform-freshid-prod'=> '055415458809', 'haystack-prod'=> '420362024408', 'Freshdesk-website'=> '516065176312', 'freshworks-redislabs-prod'=> '510741667340', 'freshworks-stratops-science-prod'=> '727456396183', 'freshworks-scylladb-prod'=> '637423319645', 'demo-engineering'=> '845756821829', 'freshdesk-migration-tool-prod'=> '613052306903', 'Freshdesk Production'=> '202227476021', 'freshconnect-prod'=> '613486529466', 'fw-secrets-service-prod'=> '101124209633', 'IT-biz-apps-prod'=> '780943320269', 'platform-whaas-prod'=> '172761185532', 'platform-aiservices-prod'=> '447877333004', 'freshcaller-prod'=> '060291706729', 'IT-Business-Analytics-Prod'=> '861289157612', 'dp-datalens-prod'=> '515527789722', 'platform-central-prod'=> '237012968983', 'Freshservice Production'=> '332436936768', 'freddy-prod'=> '252548531862', 'platform-whatsapp-prod'=> '415336696978', 'dp-baikal-datalake-ext-prod'=> '148123792793', 'platform-mcr-prod'=> '164402136073', 'dp-baikal-datalake-prod'=> '394283463826', 'freshmarketer-prod'=> '704782845794', 'dp-search-prod'=> '088973670580', 'dbaas-prod'=> '024731479175', 'freshdesk-freddy-prod'=> '379560244126', 'freshchat-prod'=> '600853678009', 'platform-freshpipe-prod'=> '515330135695', 'freshapps-prod'=> '913382441360', 'product-analytics-prod'=> '929347650758', 'freshworks-commons-prod'=> '949495201922', 'platform-freddy-prod'=> '070778426054', 'dp-freddy-prod'=> '724938948291', 'freshdesk-mercado-libre-prod'=> '414261165287', 'platform-cs-conv-prod'=> '445616970253', 'freshstatus-prod'=> '213681019941', 'freshdesk-channel-prod'=> '305479435243', 'freshchat-enterprise-prod'=> '246737834543', 'platform-antispam-prod'=> '074454382662', 'freshworks-marketplace-prod'=> '146926607606', 'freshworks-edge-prod'=> '926005369515', 'platform-freshbots-prod'=> '103813748112', 'freshsales-prod'=> '494526874241', 'platform-aloha-prod'=> '423308575901', 'fresh-orchestrator-testing'=> '799624423387', 'freshworks-soc-prod'=> '396420358689', 'platform-kairos-prod'=> '880578090170', 'platform-onboarding-prod'=> '141934252810', 'freshworks-ssl-prod'=> '537220840691', 'freshservice-apps-prod'=> '735125380913', 'freshteam-prod'=> '119865406951'}

failed_acc = []
data_list.each do |acc_name, acc_id|
  begin
    sts = Aws::STS::Client.new(region: "us-east-1")
    token  = sts.assume_role({role_arn:"arn:aws:iam::#{acc_id}:role/fusion_app",role_session_name:"freshping-staging"})
    acc_client = Aws::Account::Client.new(region: "us-east-1",access_key_id: token[:credentials][:access_key_id], secret_access_key: token[:credentials][:secret_access_key], session_token: token[:credentials][:session_token])


    resp = acc_client.list_regions({
      region_opt_status_contains: ["ENABLED", "ENABLED_BY_DEFAULT"],
    })


    active_reg = []

    resp.regions.each do |region|
        ec2_client = Aws::EC2::Client.new(region: "#{region.region_name}",access_key_id: token[:credentials][:access_key_id], secret_access_key: token[:credentials][:secret_access_key], session_token: token[:credentials][:session_token])
      begin
        resp = ec2_client.describe_instances({})
        puts "#{acc_id}|#{region.region_name}|Y"
      rescue Aws::EC2::Errors::UnauthorizedOperation => e
        puts "#{acc_id}|#{region.region_name}|N"
      end
    end
  rescue => e
    failed_acc.push("#{acc_name}|#{e}")
  end
end

puts failed_acc
