import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { App, CfnOutput, Duration, RemovalPolicy, Stack, type StackProps } from "aws-cdk-lib";
import { AttributeType, BillingMode, Table } from "aws-cdk-lib/aws-dynamodb";
import { PolicyStatement } from "aws-cdk-lib/aws-iam";
import { Code, Function as LambdaFunction, FunctionUrlAuthType, HttpMethod, Runtime } from "aws-cdk-lib/aws-lambda";
import { BlockPublicAccess, Bucket } from "aws-cdk-lib/aws-s3";
import { BucketDeployment, Source } from "aws-cdk-lib/aws-s3-deployment";
import {
  Distribution,
  Function as CfFunction,
  FunctionCode,
  FunctionEventType,
  ViewerProtocolPolicy,
} from "aws-cdk-lib/aws-cloudfront";
import { S3BucketOrigin } from "aws-cdk-lib/aws-cloudfront-origins";
import type { Construct } from "constructs";

/**
 * Bellwether stack.
 *
 * - DynamoDB: raw day feature rows, annotations, spoken checks, small
 *   metadata. Never text. Tiers and reports are derived on read.
 * - Lambda (Python 3.12): the FastAPI service behind a function URL: the
 *   dashboard API, the public features API, the MCP server (Alexa+
 *   surface) and the Bedrock-phrased weekly note. The asset is built by
 *   build-lambda.mjs without Docker: pure-Python packages plus manylinux
 *   wheels for the compiled ones, and the simulated persona bundled so the
 *   demo profile seeds itself.
 * - S3 + CloudFront: the static site, deployed when apps/web/out exists so
 *   the API can go up before the site is built.
 *
 * spaCy is not in this Lambda on purpose. Extraction runs where the
 * transcript is; only feature rows cross into this stack.
 */

const here = path.dirname(fileURLToPath(import.meta.url));
const lambdaAsset = path.join(here, "../../build/lambda");
const siteOut = path.join(here, "../../apps/web/out");

class BellwetherStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const table = new Table(this, "Profiles", {
      partitionKey: { name: "pk", type: AttributeType.STRING },
      sortKey: { name: "sk", type: AttributeType.STRING },
      billingMode: BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    if (!fs.existsSync(lambdaAsset)) {
      throw new Error(`Lambda asset missing at ${lambdaAsset}. Run: npm run build-lambda`);
    }

    const api = new LambdaFunction(this, "Api", {
      runtime: Runtime.PYTHON_3_12,
      handler: "bellwether_server.lambda.handler",
      code: Code.fromAsset(lambdaAsset),
      memorySize: 512,
      timeout: Duration.seconds(30),
      environment: {
        BELLWETHER_TABLE: table.tableName,
        BELLWETHER_BEDROCK: "1",
        BELLWETHER_FIXTURES: "/var/task/fixtures/personas",
      },
    });
    table.grantReadWriteData(api);
    api.addToRolePolicy(
      new PolicyStatement({
        actions: ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
        resources: [
          "arn:aws:bedrock:*::foundation-model/anthropic.*",
          `arn:aws:bedrock:*:${this.account}:inference-profile/*`,
        ],
      }),
    );

    const fnUrl = api.addFunctionUrl({
      authType: FunctionUrlAuthType.NONE,
      cors: {
        allowedOrigins: ["*"],
        allowedMethods: [HttpMethod.ALL],
        allowedHeaders: ["*"],
        // MCP clients must be able to read the session id off the response.
        exposedHeaders: ["MCP-Session-Id"],
      },
    });

    new CfnOutput(this, "ApiUrl", { value: fnUrl.url });
    new CfnOutput(this, "McpUrl", { value: `${fnUrl.url}mcp` });
    new CfnOutput(this, "TableName", { value: table.tableName });

    if (fs.existsSync(siteOut)) {
      const siteBucket = new Bucket(this, "Site", {
        blockPublicAccess: BlockPublicAccess.BLOCK_ALL,
        removalPolicy: RemovalPolicy.DESTROY,
        autoDeleteObjects: true,
      });
      const indexRewrite = new CfFunction(this, "IndexRewrite", {
        code: FunctionCode.fromInline(
          "function handler(event){var r=event.request;var u=r.uri;if(u.endsWith('/')){r.uri=u+'index.html';}else if(!u.includes('.')){r.uri=u+'/index.html';}return r;}",
        ),
      });
      const distribution = new Distribution(this, "SiteDistribution", {
        defaultBehavior: {
          origin: S3BucketOrigin.withOriginAccessControl(siteBucket),
          viewerProtocolPolicy: ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          functionAssociations: [{ function: indexRewrite, eventType: FunctionEventType.VIEWER_REQUEST }],
        },
        defaultRootObject: "index.html",
      });
      new BucketDeployment(this, "SiteDeployment", {
        sources: [Source.asset(siteOut)],
        destinationBucket: siteBucket,
        distribution,
        distributionPaths: ["/*"],
      });
      new CfnOutput(this, "SiteUrl", { value: `https://${distribution.distributionDomainName}` });
    }
  }
}

const app = new App();
new BellwetherStack(app, "Bellwether", {
  env: { region: process.env.CDK_DEFAULT_REGION ?? "us-east-1" },
  description: "Bellwether: speech as a vital sign. DynamoDB, Python Lambda API and MCP server, static site.",
});
